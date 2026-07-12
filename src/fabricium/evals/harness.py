"""Skill evaluation harness — infrastructure, not content.

:class:`SkillEvalHarness` handles the heavy lifting:
- Docker container lifecycle
- Multi-profile creation and configuration
- Workspace initialisation (git, seed files)
- Agent execution with trace capture
- Result collection and report generation

Callers provide the *content* — tasks, rubrics, judge prompts.
fabricium provides the *infrastructure* — containers, profiles, traces.

Usage sketch::

    from fabricium.evals import (
        SkillEvalHarness, EvalConfig, EvalTask,
        RubricSpec, RubricDimension, ScoringBand,
        JudgePrompt,
    )

    config = EvalConfig.from_env()

    tasks = [
        EvalTask(id="my-task", natural_prompt="Build a ...", ...),
    ]

    rubric = RubricSpec(task_id="my-task", dimensions=[...])

    harness = SkillEvalHarness(config)
    harness.add_profile("bare")
    harness.add_profile(
        "jovaltus-agent",
        setup_commands=["hermes jovaltus setup"],
    )

    report = harness.run(tasks, rubric)
"""  # noqa: E501

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import EvalConfig
from .judge import JudgeClient, JudgePrompt, JudgeReport
from .rubrics import RubricSpec
from .tasks import EvalTask

logger = logging.getLogger(__name__)

# ── Public types ────────────────────────────────────────────────────


@dataclass
class AgentRunResult:
    """Complete output from a single agent invocation."""

    task_id: str
    profile_name: str
    prompt_variant: str
    run_index: int

    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float

    file_tree: str
    file_contents: dict[str, str]
    build_results: str

    git_commits: list[dict[str, str]]
    subagent_count: int
    stage_keywords_found: list[str]


@dataclass
class EvalReport:
    """Top-level evaluation report.

    Callers can serialise with :meth:`to_json` or inspect the
    :attr:`task_results` and :attr:`skill_lift` fields directly.
    """

    config_summary: dict[str, Any]
    started_at: str
    completed_at: str = ""
    task_results: dict[str, list[AgentRunResult]] = field(default_factory=dict)
    verdicts: dict[str, list[JudgeReport]] = field(default_factory=dict)
    skill_lift: dict[str, Any] = field(default_factory=dict)

    def to_json(self, path: str | Path | None = None) -> str:
        """Serialise to JSON.  If *path* is given, also write to disk."""
        data: dict[str, Any] = {
            "config": self.config_summary,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "tasks": {},
            "skill_lift": self.skill_lift,
        }
        for tid, runs in self.task_results.items():
            task_verdicts = self.verdicts.get(tid, [])
            data["tasks"][tid] = {
                "runs": len(runs),
                "verdicts": [
                    {
                        "profile": v.profile_name,
                        "dimensions": v.dimensions,
                        "total": v.weighted_total,
                        "reasoning": v.reasoning_summary,
                    }
                    for v in task_verdicts
                ],
            }
        text = json.dumps(data, indent=2, ensure_ascii=False)
        if path:
            Path(path).write_text(text)
        return text


@dataclass
class ProfileSpec:
    """Specification for one profile in the evaluation."""

    name: str
    setup_commands: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)


# ── Docker helpers ──────────────────────────────────────────────────


def _docker_exec(
    container: str, *args: str, timeout: int = 120, workdir: str | None = None
) -> "subprocess.CompletedProcess[str]":
    cmd = ["docker", "exec"]
    if workdir:
        cmd += ["-w", workdir]
    cmd += [container, *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _docker_ok(container: str, *args: str, timeout: int = 120, workdir: str | None = None) -> str:
    """Run, raise on failure, return stdout."""
    proc = _docker_exec(container, *args, timeout=timeout, workdir=workdir)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Command failed (exit {proc.returncode}): {' '.join(args)}\n"
            f"stdout: {proc.stdout[:500]}\nstderr: {proc.stderr[:500]}"
        )
    return proc.stdout


def _docker_write_file(container: str, path: str, content: str, timeout: int = 30) -> None:
    """Write *content* to *path* inside the container via stdin pipe.

    Uses ``docker exec -i`` with stdin redirection — no heredoc,
    no shell escaping issues, no delimiter collision risk.
    """
    subprocess.run(
        ["docker", "exec", "-i", container, "bash", "-c", f"cat > {path}"],
        input=content,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True,
    )


# ── Main harness ────────────────────────────────────────────────────


class SkillEvalHarness:
    """Infrastructure harness for skill evaluation.

    Handles Docker container lifecycle, profile setup, workspace
    management, agent execution, and trace capture.  Callers supply
    tasks, rubrics, and judge configuration.

    Parameters
    ----------
    config:
        :class:`EvalConfig` with candidate/judge models and paths.
    judge_prompt:
        Optional custom :class:`JudgePrompt`.  If omitted, uses the
        built-in default.
    """

    def __init__(
        self,
        config: EvalConfig,
        judge_prompt: JudgePrompt | None = None,
    ):
        self.config = config
        self._judge_prompt = judge_prompt
        self._profiles: list[ProfileSpec] = []
        self._container: str = ""
        self._temp_dir: Path | None = None
        self._hermes_home: Path | None = None

    # ── Profile management ──────────────────────────────────────

    def add_profile(
        self,
        name: str,
        setup_commands: list[str] | None = None,
        skills: list[str] | None = None,
    ) -> "SkillEvalHarness":
        """Register a profile to evaluate.

        Parameters
        ----------
        name:
            Profile name (e.g. ``"bare"``, ``"jovaltus-agent"``).
        setup_commands:
            Shell commands to run inside the container after profile
            creation (e.g. ``["hermes jovaltus setup"]``).
        skills:
            Skill names to pre-load for this profile.
        """
        self._profiles.append(
            ProfileSpec(
                name=name,
                setup_commands=list(setup_commands or []),
                skills=list(skills or []),
            )
        )
        return self

    # ── Main entry point ────────────────────────────────────────

    def run(
        self,
        tasks: list[EvalTask],
        rubric: RubricSpec,
        *,
        runs_per_task: int | None = None,
    ) -> EvalReport:
        """Execute the full evaluation pipeline.

        Parameters
        ----------
        tasks:
            One or more :class:`EvalTask` instances.
        rubric:
            A :class:`RubricSpec` shared across all tasks.
        runs_per_task:
            Number of runs per task per profile variant.
            Defaults to ``config.runs_per_task``.

        Returns
        -------
        :class:`EvalReport` with all results, verdicts, and Skill Lift.
        """
        if not self._profiles:
            raise RuntimeError("No profiles registered. Call add_profile() first.")

        n_runs = runs_per_task if runs_per_task is not None else self.config.runs_per_task
        report = EvalReport(
            config_summary={
                "candidate": f"{self.config.candidate.provider}/{self.config.candidate.model}",
                "judge": f"{self.config.judge.provider}/{self.config.judge.model}",
                "profiles": [p.name for p in self._profiles],
                "tasks": [t.id for t in tasks],
                "runs_per_task": n_runs,
            },
            started_at=datetime.now().isoformat(),
        )

        judge = JudgeClient(config=self.config.judge)
        if self._judge_prompt is not None:
            judge.prompt = self._judge_prompt

        self._start_container()
        try:
            self._setup_profiles()

            for task in tasks:
                print(f"\n── {task.name} ({task.id}) ──")
                ws = self._init_workspace(task)
                all_runs: list[AgentRunResult] = []

                for prof in self._profiles:
                    variants = self._prompt_variants(task, prof)
                    for variant_label, prompt in variants:
                        print(f"  {prof.name}/{variant_label} ({n_runs} runs)...")
                        self._reset_workspace(task, ws)
                        for i in range(n_runs):
                            print(f"    run {i + 1}/{n_runs}...", end=" ", flush=True)
                            r = self._run_agent(task, prof.name, prompt, ws, variant_label, i + 1)
                            all_runs.append(r)
                            print(f"exit={r.exit_code} ({r.duration_seconds}s)")

                report.task_results[task.id] = all_runs

                # Judge the last run of each profile variant
                print("  judging...")
                verdicts = self._judge_task(task, rubric, all_runs, judge)
                report.verdicts[task.id] = verdicts
                if len(verdicts) >= 2:
                    lift = round(verdicts[1].weighted_total - verdicts[0].weighted_total, 2)
                    print(
                        f"    bare: {verdicts[0].weighted_total}  "
                        f"jovaltus: {verdicts[1].weighted_total}  lift: {lift}"
                    )

            report.skill_lift = self._compute_lift(report, rubric)

        finally:
            if not self.config.keep:
                self._stop_container()

        report.completed_at = datetime.now().isoformat()
        return report

    # ── Container ───────────────────────────────────────────────

    def _start_container(self) -> None:
        self._temp_dir = Path(tempfile.mkdtemp(prefix="fabricium-eval-"))
        hh = self._temp_dir / ".hermes"
        hh.mkdir(parents=True, exist_ok=True)
        for sub in ["plugins", "skills", "profiles"]:
            (hh / sub).mkdir(exist_ok=True)

        (hh / "config.yaml").write_text(
            self._build_hermes_config_yaml(
                self.config.candidate.provider,
                self.config.candidate.model,
                self.config.candidate.api_base,
            )
        )
        env_key = self._api_key_env_name(self.config.candidate.provider)
        (hh / ".env").write_text(f"{env_key}={self.config.candidate.api_key}\n")

        # Copy jovaltus plugin
        jdst = hh / "plugins" / "jovaltus"
        shutil.copytree(self.config.jovaltus_plugin_dir, jdst, symlinks=True, dirs_exist_ok=True)

        self._container = f"fabricium-eval-{os.getpid()}"
        cmd: list[str] = [
            "docker",
            "run",
            "--rm",
            "-d",
            "--network",
            self.config.docker_network,
            "--name",
            self._container,
            "-v",
            f"{hh}:/opt/data",
            "-e",
            f"{env_key}={self.config.candidate.api_key}",
        ]
        if self.config.fabricium_src and self.config.fabricium_src.exists():
            cmd += ["-v", f"{self.config.fabricium_src}:/opt/fabricium:ro"]
        cmd += [self.config.docker_image, "sleep", "infinity"]
        subprocess.run(cmd, check=True, capture_output=True, timeout=60)

        if self.config.fabricium_src:
            subprocess.run(
                [
                    "docker",
                    "exec",
                    "-e",
                    "HERMES_DOCKER_EXEC_AS_ROOT=1",
                    self._container,
                    "uv",
                    "pip",
                    "install",
                    "--python",
                    "/opt/hermes/.venv/bin/python3",
                    "-e",
                    "/opt/fabricium",
                ],
                check=True,
                capture_output=True,
                timeout=120,
            )

        _docker_ok(self._container, "hermes", "plugins", "enable", "jovaltus")

        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if _docker_exec(self._container, "hermes", "--version").returncode == 0:
                break
            time.sleep(1.0)

        self._hermes_home = hh

    def _stop_container(self) -> None:
        if self._container:
            subprocess.run(["docker", "rm", "-f", self._container], capture_output=True, timeout=30)
        if self._temp_dir and self._temp_dir.exists():
            shutil.rmtree(self._temp_dir, ignore_errors=True)

    # ── Profiles ────────────────────────────────────────────────

    # Providers that Hermes knows about without custom_providers config.
    # Anything not in this set is treated as custom and auto-configured.
    _STANDARD_PROVIDERS: set[str] = {
        "openai",
        "anthropic",
        "deepseek",
        "google",
        "openrouter",
        "groq",
        "xai",
        "ollama",
        "together",
        "fireworks",
        "mistral",
        "voyage",
        "cohere",
        "perplexity",
    }

    @classmethod
    def _provider_ref(cls, provider: str, api_base: str) -> str:
        """Return the Hermes provider reference for a given provider.

        Standard providers are used as-is.  Custom providers (everything
        else) are wrapped as ``custom:<name>`` so Hermes knows to look
        for a ``custom_providers`` block.
        """
        clean = provider.strip()
        if clean in cls._STANDARD_PROVIDERS:
            return clean
        if clean.startswith("http://") or clean.startswith("https://"):
            return clean
        return f"custom:{clean}"

    @classmethod
    def _build_hermes_config_yaml(cls, provider: str, model: str, api_base: str) -> str:
        """Build a Hermes ``config.yaml`` fragment for a model config.

        When *api_base* is set or *provider* is not a standard provider,
        a ``custom_providers`` block is automatically included so Hermes
        knows the API endpoint.

        The base URL is normalised to include ``/v1`` (the standard
        OpenAI-compatible API prefix) if not already present.
        """
        provider_ref = cls._provider_ref(provider, api_base)

        lines: list[str] = [
            "model:",
            f'  default: "{model}"',
            f'  provider: "{provider_ref}"',
        ]

        # Emit custom_providers if needed (Hermes requires YAML list format)
        if api_base or provider_ref.startswith("custom:") or provider_ref.startswith("http"):
            pname = (
                provider_ref.split(":", 1)[-1] if provider_ref.startswith("custom:") else provider
            )
            base = api_base if api_base else f"https://api.{pname}.com"
            # Normalise: ensure /v1 prefix for OpenAI-compatible APIs
            if not base.rstrip("/").endswith("/v1"):
                base = base.rstrip("/") + "/v1"
            key_env = f"{pname.upper()}_API_KEY"
            lines.append("custom_providers:")
            lines.append(f"  - name: {pname}")
            lines.append(f'    base_url: "{base.rstrip("/")}"')
            lines.append(f"    key_env: {key_env}")

        lines.append("agent:")
        lines.append("  max_turns: 150")
        lines.append("terminal:")
        lines.append("  backend: local")

        return "\n".join(lines)

    @classmethod
    def _api_key_env_name(cls, provider: str) -> str:
        """Return the env-var name Hermes uses for this provider's API key."""
        clean = provider.strip()
        if clean.startswith("custom:"):
            clean = clean.split(":", 1)[1]
        if clean.startswith("http"):
            # Can't derive a sensible env var from a URL — caller must handle
            return f"{clean.upper()}_API_KEY"
        return f"{clean.upper()}_API_KEY"

    def _setup_profiles(self) -> None:
        for prof in self._profiles:
            _docker_ok(self._container, "hermes", "profile", "create", prof.name)
            self._write_profile_config(prof.name)
            for cmd in prof.setup_commands:
                _docker_exec(self._container, "bash", "-c", cmd, timeout=120)

    def _write_profile_config(self, name: str) -> None:
        yaml = self._build_hermes_config_yaml(
            self.config.candidate.provider,
            self.config.candidate.model,
            self.config.candidate.api_base,
        )
        pd = f"/opt/data/profiles/{name}"
        _docker_ok(self._container, "mkdir", "-p", pd)
        _docker_write_file(self._container, f"{pd}/config.yaml", yaml)

    # ── Workspace ───────────────────────────────────────────────

    def _init_workspace(self, task: EvalTask) -> str:
        ws = f"{self.config.workspace_base}/{task.workspace_subdir}"
        _docker_ok(self._container, "mkdir", "-p", self.config.workspace_base)
        _docker_ok(self._container, "mkdir", "-p", ws)
        for rel, content in task.seed_files.items():
            fp = f"{ws}/{rel}"
            _docker_ok(self._container, "mkdir", "-p", str(Path(fp).parent))
            _docker_write_file(self._container, fp, content)
        _docker_ok(self._container, "git", "init", workdir=ws)
        _docker_ok(
            self._container, "git", "config", "user.email", "eval@fabricium.test", workdir=ws
        )
        _docker_ok(self._container, "git", "config", "user.name", "Fabricium Eval", workdir=ws)
        _docker_ok(self._container, "git", "add", "-A", workdir=ws)
        _docker_ok(self._container, "git", "commit", "-m", "init", workdir=ws)
        # Hermes agent runs as the 'hermes' user; everything above is created
        # by docker exec (root).  chown last so .git, seed files, and the
        # working tree are all accessible to the agent.
        _docker_ok(self._container, "chown", "-R", "hermes:hermes", self.config.workspace_base)
        return ws

    def _reset_workspace(self, task: EvalTask, ws: str) -> None:
        _docker_exec(
            self._container,
            "bash",
            "-c",
            f"cd {ws} && git clean -fd && git checkout -- .",
            timeout=30,
        )

    # ── Agent execution ─────────────────────────────────────────

    def _prompt_variants(self, task: EvalTask, prof: ProfileSpec) -> list[tuple[str, str]]:
        """Return (variant_label, prompt) pairs for a task+profile combo."""
        variants: list[tuple[str, str]] = []
        if task.natural_prompt:
            variants.append(("natural", task.natural_prompt))
        if task.explicit_prompt and task.explicit_prompt != task.natural_prompt:
            variants.append(("explicit", task.explicit_prompt))
        if not variants:
            raise ValueError(f"Task {task.id} has no prompts defined")
        return variants

    def _run_agent(
        self,
        task: EvalTask,
        profile: str,
        prompt: str,
        workspace: str,
        variant: str,
        index: int,
    ) -> AgentRunResult:
        start = time.monotonic()

        pf = f"/tmp/eval_prompt_{os.getpid()}.txt"
        _docker_write_file(self._container, pf, prompt)

        stdout = ""
        stderr = ""
        exit_code = -1

        try:
            proc = _docker_exec(
                self._container,
                "hermes",
                "-p",
                profile,
                "chat",
                "-q",
                f"$(cat {pf})",
                timeout=self.config.task_timeout,
                workdir=workspace,
            )
            stdout = proc.stdout
            stderr = proc.stderr
            exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            duration = round(time.monotonic() - start, 1)
            print(f"TIMEOUT after {duration}s", end=" ", flush=True)
            stdout = ""
            stderr = f"[TIMEOUT] Agent did not finish within {self.config.task_timeout}s"
            exit_code = -1

        duration = round(time.monotonic() - start, 1)

        # File tree
        ft = _docker_exec(
            self._container,
            "find",
            workspace,
            "-type",
            "f",
            "-not",
            "-path",
            "*/.git/*",
            timeout=30,
        ).stdout

        # File contents (cap 10 files, 3000 chars each)
        fc: dict[str, str] = {}
        for p in ft.strip().split("\n")[:10]:
            p = p.strip()
            if not p:
                continue
            try:
                out = _docker_exec(self._container, "cat", p, timeout=10).stdout
                fc[p] = out[:3000]
            except Exception:
                fc[p] = "[read error]"

        # Build/test results
        parts: list[str] = []
        for desc, cmd in task.verify_commands:
            vr = _docker_exec(self._container, "bash", "-c", cmd, timeout=120)
            parts.append(f"### {desc} (exit={vr.returncode})\n{vr.stdout[:1000]}")
        br = "\n\n".join(parts)

        # Git evidence
        gl = _docker_exec(
            self._container,
            "git",
            "log",
            "--oneline",
            "--all",
            workdir=workspace,
        ).stdout
        commits: list[dict[str, str]] = []
        for line in gl.strip().split("\n"):
            if line.strip():
                parts_line = line.strip().split(" ", 1)
                commits.append(
                    {
                        "hash": parts_line[0],
                        "message": parts_line[1] if len(parts_line) > 1 else "",
                    }
                )

        # Subagent / stage evidence
        combined = stdout + stderr
        sc = (
            combined.count("delegate_task")
            + combined.count("jovaltus_implement")
            + combined.count("jovaltus_verify")
            + combined.count("jovaltus_simplify")
        )
        sk: list[str] = []
        for kw in ["implementing", "verifying", "simplifying", "planning"]:
            if kw in combined.lower():
                sk.append(kw)

        return AgentRunResult(
            task_id=task.id,
            profile_name=profile,
            prompt_variant=variant,
            run_index=index,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=duration,
            file_tree=ft,
            file_contents=fc,
            build_results=br,
            git_commits=commits,
            subagent_count=sc,
            stage_keywords_found=sk,
        )

    # ── Judging ─────────────────────────────────────────────────

    def _judge_task(
        self,
        task: EvalTask,
        rubric: RubricSpec,
        runs: list[AgentRunResult],
        judge: JudgeClient,
    ) -> list[JudgeReport]:
        """Judge each profile's output. Returns one verdict per profile."""
        verdicts: list[JudgeReport] = []
        profiles_seen: set[str] = set()

        for run in reversed(runs):
            if run.profile_name in profiles_seen:
                continue
            profiles_seen.add(run.profile_name)

            report = judge.evaluate(
                task_prompt=task.natural_prompt or task.explicit_prompt,
                profile_name=run.profile_name,
                file_tree=run.file_tree,
                file_contents=self._fmt_fc(run.file_contents),
                build_results=run.build_results,
                trace_summary=(
                    f"exit_code={run.exit_code} "
                    f"duration={run.duration_seconds}s "
                    f"subagent_calls={run.subagent_count} "
                    f"git_commits={len(run.git_commits)} "
                    f"stage_keywords={run.stage_keywords_found}"
                ),
                rubric=rubric,
            )
            verdicts.append(report)
        return verdicts

    # ── Report ──────────────────────────────────────────────────

    def _compute_lift(self, report: EvalReport, rubric: RubricSpec) -> dict[str, Any]:
        lifts: dict[str, Any] = {}
        for tid, runs in report.task_results.items():
            by_profile: dict[str, list[AgentRunResult]] = {}
            for r in runs:
                by_profile.setdefault(r.profile_name, []).append(r)

            verdicts = report.verdicts.get(tid, [])
            if len(verdicts) < 2:
                lifts[tid] = {"error": "need ≥2 verdicts for lift"}
                continue

            bare = verdicts[0].weighted_total
            skill = verdicts[1].weighted_total if len(verdicts) > 1 else 0.0

            dim_deltas: dict[str, float] = {}
            for d in rubric.universal_dimensions:
                dim_deltas[d.id] = round(
                    verdicts[1].dimensions.get(d.id, 0) - verdicts[0].dimensions.get(d.id, 0),
                    2,
                )

            hook: dict[str, Any] = {}
            for pname, pruns in by_profile.items():
                hook[pname] = {
                    "subagent_calls": sum(r.subagent_count for r in pruns),
                    "git_commits": max((len(r.git_commits) for r in pruns), default=0),
                    "avg_duration_s": (
                        sum(r.duration_seconds for r in pruns) / len(pruns) if pruns else 0
                    ),
                }

            lifts[tid] = {
                "bare_score": bare,
                "skill_score": skill,
                "skill_lift": round(skill - bare, 2),
                "dimension_deltas": dim_deltas,
                "hook_evidence": hook,
            }
        return lifts

    @staticmethod
    def _fmt_fc(fc: dict[str, str]) -> str:
        parts: list[str] = []
        for p, c in list(fc.items())[:10]:
            parts.append(f"### {p}\n```\n{c[:3000]}\n```")
        return "\n\n".join(parts)
