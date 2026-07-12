"""LLM-as-Judge client for skill evaluation.

Sends agent outputs + caller-defined rubrics to a judge model and
parses structured verdicts.  Uses direct HTTP calls (no SDK dependency).

The judge prompt template is fully customisable — callers provide their
own system prompt via :class:`JudgePrompt`.  fabricium handles API
communication, retries, structured-output parsing, and calibration.

Design rules:
- **Cross-provider judge**: use a different provider family than the
  candidate to avoid self-preference bias.
- **Position randomisation**: bare/skill outputs are shuffled before
  sending to the judge.
- **Reasoning before score**: the default prompt template forces
  chain-of-thought before numeric scores.
"""

from __future__ import annotations

import json
import logging
import random
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from .config import ModelConfig
from .rubrics import RubricSpec

logger = logging.getLogger(__name__)

# ── Public types ────────────────────────────────────────────────────


@dataclass
class JudgePrompt:
    """Caller-defined judge prompt template.

    Both fields support ``{placeholders}`` that are filled at evaluation
    time.  See :meth:`JudgeClient.evaluate` for the full list.
    """

    system: str
    user: str


@dataclass
class JudgeVerdict:
    """A single dimension's score with reasoning."""

    task_id: str
    profile_name: str
    dimension: str
    score: int
    reasoning: str


@dataclass
class JudgeReport:
    """Complete judge evaluation for one task under one profile."""

    task_id: str
    profile_name: str
    dimensions: dict[str, float]
    reasoning_summary: str
    weighted_total: float
    raw_response: str = ""


# ── Default judge prompt ────────────────────────────────────────────

DEFAULT_JUDGE_PROMPT = JudgePrompt(
    system="""You are an expert code reviewer evaluating agent outputs
for a software engineering task.  You MUST return a valid JSON object
matching the EXACT schema provided.

## Protocol
1. Read the TASK REQUIREMENTS.
2. Read the AGENT OUTPUT (code files, build/test results, trace summary).
3. For EACH rubric dimension:
   a. State your evidence (cite file paths, build results, tool calls).
   b. Match the evidence against the scoring bands.
   c. Choose the SINGLE band whose criteria BEST matches.
      Do NOT interpolate — pick the closest one.
4. Write a brief reasoning summary.

## Rules
- Score the OUTPUT, not the prompt or task difficulty.
- If evidence is missing, score 0 and explain why.
- Do NOT inflate scores for verbose output.
- Be strict but fair.  7+ requires concrete evidence.""",
    user="""## TASK
{task_prompt}

## PROFILE
{profile_name}

## AGENT OUTPUT

### Files Created / Modified
{file_tree}

### Key File Contents
{file_contents}

### Build / Test Results
{build_results}

### Agent Trace Summary
{trace_summary}

## RUBRIC
{rubric_json}

## INSTRUCTIONS
Evaluate the agent's output against each rubric dimension.
Return your evaluation as EXACT JSON with this schema:

{{
  "task_id": "{task_id}",
  "profile_name": "{profile_name}",
  "reasoning_summary": "2-3 sentence overview.",
  "dimensions": {{
    "<dimension_id>": {{
      "score": <integer>,
      "reasoning": "Specific evidence for this score."
    }}
  }}
}}

Return ONLY valid JSON.  No markdown fences, no extra text.""",
)


# ── Judge client ────────────────────────────────────────────────────


@dataclass
class JudgeClient:
    """Sends evaluation requests to a judge model and parses verdicts.

    Parameters
    ----------
    config:
        Judge model configuration (provider, model, API key).
    prompt:
        Caller-defined prompt template.  If omitted, uses
        :data:`DEFAULT_JUDGE_PROMPT`.
    temperature:
        Judge temperature (default 0.0 for deterministic scoring).
    max_tokens:
        Max tokens for the judge response.
    """

    config: ModelConfig
    prompt: JudgePrompt = field(default_factory=lambda: DEFAULT_JUDGE_PROMPT)
    temperature: float = 0.0
    max_tokens: int = 4096
    _retries: int = 3

    def evaluate(
        self,
        task_prompt: str,
        profile_name: str,
        file_tree: str,
        file_contents: str,
        build_results: str,
        trace_summary: str,
        rubric: RubricSpec,
    ) -> JudgeReport:
        """Run the judge on one task result.

        Placeholders available in the caller's prompt template:

        - ``{task_prompt}`` — the task description shown to the agent
        - ``{task_id}`` — the task identifier
        - ``{profile_name}`` — profile name (``bare`` or ``jovaltus-agent``)
        - ``{file_tree}`` — file tree of the agent's workspace
        - ``{file_contents}`` — key file contents (capped)
        - ``{build_results}`` — build/test command outputs
        - ``{trace_summary}`` — abbreviated agent trace
        - ``{rubric_json}`` — serialised rubric with scoring bands
        """
        rubric_json = json.dumps(rubric.to_judge_json(), indent=2)

        system = self.prompt.system
        user = self.prompt.user.format(
            task_prompt=task_prompt,
            task_id=rubric.task_id,
            profile_name=profile_name,
            file_tree=file_tree,
            file_contents=file_contents,
            build_results=build_results,
            trace_summary=trace_summary,
            rubric_json=rubric_json,
        )

        raw = self._call_api(system, user)
        report = self._parse_response(raw, rubric, profile_name)
        report.raw_response = raw
        return report

    def evaluate_pair(
        self,
        task_prompt: str,
        bare_summary: dict[str, str],
        jovaltus_summary: dict[str, str],
        rubric: RubricSpec,
    ) -> tuple[JudgeReport, JudgeReport]:
        """Evaluate bare and skill-equipped outputs.

        Randomises evaluation order to avoid position bias.
        Returns ``(bare_report, jovaltus_report)`` in canonical order.
        """
        order = ["bare", "jovaltus"]
        random.shuffle(order)

        reports: dict[str, JudgeReport] = {}
        for name in order:
            summary = bare_summary if name == "bare" else jovaltus_summary
            reports[name] = self.evaluate(
                task_prompt=task_prompt,
                profile_name=name,
                **summary,
                rubric=rubric,
            )

        return reports["bare"], reports["jovaltus"]

    # ── API calls ────────────────────────────────────────────────

    def _call_api(self, system: str, user: str) -> str:
        if self.config.provider == "anthropic":
            return self._call_anthropic(system, user)
        return self._call_openai_compatible(system, user)

    def _call_openai_compatible(self, system: str, user: str) -> str:
        url = self._resolve_base_url()
        body_dict: dict[str, Any] = {
            "model": self.config.model,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        # max_tokens is intentionally NOT set — reasoning models
        # consume tokens for chain-of-thought, and a fixed cap can
        # starve the final content output.
        body = json.dumps(body_dict).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}",
            },
        )

        last_error = ""
        logger.info(
            "Judge request: url=%s model=%s body_len=%d",
            url,
            self.config.model,
            len(body),
        )
        for attempt in range(1, self._retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    raw_bytes = resp.read()
                    data = json.loads(raw_bytes.decode("utf-8"))
                msg = data["choices"][0]["message"]
                # DeepSeek V4 thinking mode: content may be empty while
                # reasoning_content holds the actual output.  Fall back.
                content = msg.get("content") or msg.get("reasoning_content", "")
                logger.info(
                    "Judge response: content_len=%d reasoning_len=%d preview=%s",
                    len(msg.get("content") or ""),
                    len(msg.get("reasoning_content") or ""),
                    repr(content[:200]),
                )
                return str(content)
            except (urllib.error.URLError, urllib.error.HTTPError) as e:
                last_error = str(e)
            except (KeyError, json.JSONDecodeError) as e:
                last_error = f"Parse: {e}"

        raise RuntimeError(f"Judge API failed after {self._retries} attempts: {last_error}")

    def _call_anthropic(self, system: str, user: str) -> str:
        url = "https://api.anthropic.com/v1/messages"
        body = json.dumps(
            {
                "model": self.config.model,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.config.api_key,
                "anthropic-version": "2023-06-01",
            },
        )

        last_error = ""
        for attempt in range(1, self._retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                for block in data["content"]:
                    if block["type"] == "text":
                        return str(block["text"])
                raise RuntimeError("No text in Anthropic response")
            except (urllib.error.URLError, urllib.error.HTTPError) as e:
                last_error = str(e)
            except (KeyError, json.JSONDecodeError) as e:
                last_error = f"Parse: {e}"

        raise RuntimeError(f"Judge API failed after {self._retries} attempts: {last_error}")

    def _resolve_base_url(self) -> str:
        # Explicit api_base always wins — handles self-hosted / aggregated gateways
        if self.config.api_base:
            base = self.config.api_base.rstrip("/")
            # If the base already ends with /chat/completions, don't append again
            if base.endswith("/chat/completions"):
                return base
            return f"{base}/v1/chat/completions"

        provider_map: dict[str, str] = {
            "openai": "https://api.openai.com/v1/chat/completions",
            "deepseek": "https://api.deepseek.com/v1/chat/completions",
            "openrouter": "https://openrouter.ai/api/v1/chat/completions",
            "google": ("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"),
            "groq": "https://api.groq.com/openai/v1/chat/completions",
            "xai": "https://api.x.ai/v1/chat/completions",
        }
        if self.config.provider in provider_map:
            return provider_map[self.config.provider]
        if self.config.provider.startswith("http"):
            return f"{self.config.provider.rstrip('/')}/chat/completions"
        return "https://openrouter.ai/api/v1/chat/completions"

    # ── Response parsing ─────────────────────────────────────────

    def _parse_response(self, raw: str, rubric: RubricSpec, profile_name: str) -> JudgeReport:
        json_str = raw.strip()
        if json_str.startswith("```"):
            lines = json_str.split("\n")
            start, end = 0, len(lines)
            for i, line in enumerate(lines):
                if "{" in line and start == 0:
                    start = i
                if "}" in line:
                    end = i + 1
            json_str = "\n".join(lines[start:end])

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            import re

            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError:
                    data = None
            else:
                data = None

        if data is None or not isinstance(data, dict):
            # Judge returned non-JSON — fall back to zero scores
            import warnings

            warnings.warn(
                f"Judge returned non-JSON response for {profile_name} — "
                f"scoring all dimensions as 0. First 200 chars: {raw[:200]}"
            )
            return JudgeReport(
                task_id=rubric.task_id,
                profile_name=profile_name,
                dimensions={d.id: 0.0 for d in rubric.dimensions},
                reasoning_summary=f"Judge parsing failed. Raw: {raw[:200]}",
                weighted_total=0.0,
                raw_response=raw,
            )

        dimensions: dict[str, float] = {}
        raw_dims = data.get("dimensions", {})
        for dim in rubric.dimensions:
            dim_data = raw_dims.get(dim.id, {})
            score = dim_data.get("score", 0)
            if not isinstance(score, (int, float)):
                score = 0
            dimensions[dim.id] = float(score)

        total = 0.0
        for dim in rubric.dimensions:
            total += dimensions.get(dim.id, 0.0) * dim.weight

        return JudgeReport(
            task_id=rubric.task_id,
            profile_name=profile_name,
            dimensions=dimensions,
            reasoning_summary=str(data.get("reasoning_summary", "")),
            weighted_total=round(total, 2),
        )


# ── Calibration ─────────────────────────────────────────────────────


def calibrate(
    human_labels: list[dict[str, Any]],
    judge_reports: list[JudgeReport],
) -> dict[str, Any]:
    """Compute judge-human agreement metrics.

    Parameters
    ----------
    human_labels:
        List of dicts with ``task_id``, ``dimension``, ``score`` keys.
    judge_reports:
        List of :class:`JudgeReport` instances for the same tasks.

    Returns
    -------
    dict with ``agreement_pct``, ``cohens_kappa``, ``spearman_rho``,
    ``n_pairs``, and ``per_dimension`` breakdown.
    """
    paired: dict[str, tuple[list[int], list[int]]] = {}
    for hl in human_labels:
        key = f"{hl['task_id']}/{hl['dimension']}"
        if key not in paired:
            paired[key] = ([], [])
        paired[key][0].append(int(hl["score"]))

    for report in judge_reports:
        for dim_id, score in report.dimensions.items():
            key = f"{report.task_id}/{dim_id}"
            if key in paired:
                paired[key][1].append(int(score))

    all_human: list[int] = []
    all_judge: list[int] = []
    for hs, js in paired.values():
        for h, j in zip(hs, js):
            all_human.append(h)
            all_judge.append(j)

    if not all_human:
        return {"error": "No paired labels for calibration"}

    agreements = sum(1 for h, j in zip(all_human, all_judge) if h == j)
    agreement_pct = round(agreements / len(all_human) * 100, 1)

    def _rank_simple(data: list[int]) -> list[float]:
        su = sorted(set(data))
        rm = {v: float(i + 1) for i, v in enumerate(su)}
        return [rm[v] for v in data]

    try:
        hr = _rank_simple(all_human)
        jr = _rank_simple(all_judge)
        n = len(hr)
        d2 = sum((h - j) ** 2 for h, j in zip(hr, jr))
        spearman = round(1 - (6 * d2) / (n * (n**2 - 1)), 3) if n > 1 else 1.0
    except Exception:
        spearman = None

    try:
        cats = sorted(set(all_human) | set(all_judge))
        n = len(all_human)
        observed = sum(1 for h, j in zip(all_human, all_judge) if h == j) / n
        hc = Counter(all_human)
        jc = Counter(all_judge)
        expected = sum((hc.get(c, 0) / n) * (jc.get(c, 0) / n) for c in cats)
        kappa = round((observed - expected) / (1 - expected), 3) if expected < 1 else 1.0
    except Exception:
        kappa = None

    return {
        "agreement_pct": agreement_pct,
        "cohens_kappa": kappa,
        "spearman_rho": spearman,
        "n_pairs": len(all_human),
    }
