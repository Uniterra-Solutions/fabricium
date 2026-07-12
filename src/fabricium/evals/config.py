"""Environment-variable-driven configuration for skill evaluations.

All model credentials, provider names, and operational parameters are read
from environment variables.  No secrets in code, no config files to edit.

Quick start::

    export EVAL_CANDIDATE_PROVIDER=deepseek
    export EVAL_CANDIDATE_MODEL=deepseek/deepseek-chat
    export EVAL_CANDIDATE_API_KEY=sk-...

    export EVAL_JUDGE_PROVIDER=anthropic
    export EVAL_JUDGE_MODEL=anthropic/claude-sonnet-4
    export EVAL_JUDGE_API_KEY=sk-ant-...

    python -m fabricium.evals.runner
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# ── public types ────────────────────────────────────────────────────


@dataclass
class ModelConfig:
    """Provider + model + credential + endpoint.

    ``api_base`` is optional — when set it overrides the default
    endpoint for the provider.  Useful for self-hosted or aggregated
    providers (e.g. OpenRouter-compatible gateways).
    """

    provider: str
    model: str
    api_key: str = ""
    api_base: str = ""

    @property
    def is_configured(self) -> bool:
        return bool(self.provider and self.model and self.api_key)


@dataclass
class EvalConfig:
    """Complete evaluation configuration — all from environment variables."""

    # Candidate (the agent being evaluated)
    candidate: ModelConfig

    # Judge (the LLM that scores agent outputs)
    judge: ModelConfig

    # Paths
    jovaltus_plugin_dir: Path
    output_dir: Path = field(default_factory=lambda: Path.cwd() / "eval_results")
    fabricium_src: Path | None = None

    # Docker
    docker_image: str = "nousresearch/hermes-agent:latest"
    docker_network: str = "host"
    keep: bool = False

    # Execution
    tasks: list[str] = field(default_factory=lambda: ["all"])
    runs_per_task: int = 3
    task_timeout: int = 900  # seconds (15 min per run)

    # Workspace base inside container
    workspace_base: str = "/workspace"


# ── env-var loading ─────────────────────────────────────────────────


def _require_env(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        raise RuntimeError(
            f"Missing required environment variable: {name}\n  export {name}=<value>"
        )
    return val


def _model_from_prefix(prefix: str) -> ModelConfig:
    """Read EVAL_{PREFIX}_PROVIDER / MODEL / API_KEY / API_BASE from env."""
    return ModelConfig(
        provider=_require_env(f"EVAL_{prefix}_PROVIDER"),
        model=_require_env(f"EVAL_{prefix}_MODEL"),
        api_key=os.environ.get(f"EVAL_{prefix}_API_KEY", ""),
        api_base=os.environ.get(f"EVAL_{prefix}_API_BASE", ""),
    )


def _discover_fabricium_src() -> Path | None:
    """Walk up from this file to find the fabricium source root."""
    here = Path(__file__).resolve().parent
    for parent in [here] + list(here.parents):
        if (parent / "pyproject.toml").exists():
            return parent
    return None


def load_config() -> EvalConfig:
    """Build an :class:`EvalConfig` from environment variables.

    Required env vars
    -----------------
    ``EVAL_CANDIDATE_PROVIDER``
        Provider for the agent being tested (e.g. ``deepseek``).
    ``EVAL_CANDIDATE_MODEL``
        Model for the agent (e.g. ``deepseek/deepseek-chat``).
    ``EVAL_JUDGE_PROVIDER``
        Provider for the LLM judge (e.g. ``anthropic``).
    ``EVAL_JUDGE_MODEL``
        Model for the judge (e.g. ``anthropic/claude-sonnet-4``).
    ``EVAL_JOVALTUS_PLUGIN_DIR``
        Absolute path to the Jovaltus plugin source directory.

    Optional env vars
    -----------------
    ``EVAL_CANDIDATE_API_KEY``
        API key for the candidate provider.  Falls back to
        ``<PROVIDER>_API_KEY`` in the environment.
    ``EVAL_JUDGE_API_KEY``
        API key for the judge provider.  Falls back to
        ``<PROVIDER>_API_KEY`` in the environment.
    ``EVAL_CANDIDATE_API_BASE``
        Override the default API endpoint for the candidate provider.
        Useful for self-hosted or aggregated gateways
        (e.g. ``https://api.uniterra-solutions.com``).
    ``EVAL_JUDGE_API_BASE``
        Override the default API endpoint for the judge provider.
    ``EVAL_FABRICIUM_SRC``
        Override the auto-discovered fabricium source path.
        Set empty string to skip fabricium install.
    ``EVAL_DOCKER_IMAGE``
        Docker image (default: ``nousresearch/hermes-agent:latest``).
    ``EVAL_DOCKER_NETWORK``
        Docker network mode (default: ``host``).  Use ``host`` so the
        container can reach internal/self-hosted services on the host
        machine (e.g. tailnet-connected private APIs).
    ``EVAL_TASKS``
        Comma-separated task ids or ``all`` (default: ``all``).
    ``EVAL_RUNS_PER_TASK``
        Number of runs per task per profile variant (default: ``3``).
    ``EVAL_TASK_TIMEOUT``
        Per-run timeout in seconds (default: ``900``).
    ``EVAL_KEEP``
        Set to ``1`` to keep the Docker container after completion.
    ``EVAL_OUTPUT_DIR``
        Directory for eval reports (default: ``./eval_results`` relative
        to the current working directory).
    """
    # Candidate
    candidate = _model_from_prefix("CANDIDATE")
    if not candidate.api_key:
        provider_key = f"{candidate.provider.upper()}_API_KEY"
        candidate.api_key = os.environ.get(provider_key, "")
    if not candidate.api_key:
        raise RuntimeError(
            "Missing candidate API key.\n"
            f"  export EVAL_CANDIDATE_API_KEY=<key>\n"
            f"  or export {candidate.provider.upper()}_API_KEY=<key>"
        )

    # Judge
    judge = _model_from_prefix("JUDGE")
    if not judge.api_key:
        provider_key = f"{judge.provider.upper()}_API_KEY"
        judge.api_key = os.environ.get(provider_key, "")
    if not judge.api_key:
        raise RuntimeError(
            "Missing judge API key.\n"
            f"  export EVAL_JUDGE_API_KEY=<key>\n"
            f"  or export {judge.provider.upper()}_API_KEY=<key>"
        )

    # Provider cross-check — strongly recommended, not enforced
    if judge.provider == candidate.provider:
        import warnings

        warnings.warn(
            "Judge and candidate use the same provider. "
            "This risks self-preference bias (LLMs favour their own outputs). "
            "Consider using a different provider for the judge."
        )

    # Jovaltus plugin dir
    raw_jovaltus = _require_env("EVAL_JOVALTUS_PLUGIN_DIR")
    jovaltus_dir = Path(raw_jovaltus).resolve()
    if not jovaltus_dir.exists():
        raise RuntimeError(f"Jovaltus plugin dir not found: {jovaltus_dir}")
    if not (jovaltus_dir / "plugin.yaml").exists():
        raise RuntimeError(
            f"No plugin.yaml found in {jovaltus_dir}. Is this the right Jovaltus plugin directory?"
        )

    # Fabricium source
    raw_fabricium = os.environ.get("EVAL_FABRICIUM_SRC", "")
    if raw_fabricium == "":
        fabricium_src = None
    elif raw_fabricium:
        fabricium_src = Path(raw_fabricium).resolve()
    else:
        fabricium_src = _discover_fabricium_src()

    # Tasks
    raw_tasks = os.environ.get("EVAL_TASKS", "all").strip()
    tasks = [t.strip() for t in raw_tasks.split(",") if t.strip()]

    return EvalConfig(
        candidate=candidate,
        judge=judge,
        jovaltus_plugin_dir=jovaltus_dir,
        output_dir=Path(
            os.environ.get("EVAL_OUTPUT_DIR", str(Path.cwd() / "eval_results"))
        ).resolve(),
        fabricium_src=fabricium_src,
        docker_image=os.environ.get("EVAL_DOCKER_IMAGE", "nousresearch/hermes-agent:latest"),
        docker_network=os.environ.get("EVAL_DOCKER_NETWORK", "host"),
        keep=os.environ.get("EVAL_KEEP", "") == "1",
        tasks=tasks,
        runs_per_task=int(os.environ.get("EVAL_RUNS_PER_TASK", "3")),
        task_timeout=int(os.environ.get("EVAL_TASK_TIMEOUT", "900")),
        workspace_base=os.environ.get("EVAL_WORKSPACE_BASE", "/workspace"),
    )
