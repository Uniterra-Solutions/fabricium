"""Fabricium skill evaluation framework.

**fabricium provides the infrastructure** — Docker containers,
multi-profile setup, agent execution, trace capture, LLM judging.
**Callers provide the content** — tasks, rubrics, judge prompts.

Quick start (caller side)::

    from fabricium.evals import (
        SkillEvalHarness, EvalConfig, EvalTask,
        RubricSpec, RubricDimension, ScoringBand,
    )

    config = EvalConfig.from_env()

    tasks = [EvalTask(id="my-task", natural_prompt="Build a ...", ...)]
    rubric = RubricSpec(task_id="my-task", dimensions=[...])

    harness = SkillEvalHarness(config)
    harness.add_profile("bare")
    harness.add_profile("jovaltus-agent",
                        setup_commands=["hermes jovaltus setup"])
    report = harness.run(tasks, rubric)
    report.to_json("eval_results/report.json")

Modules
-------
``config``
    Environment-variable-driven :class:`EvalConfig`.
``tasks``
    :class:`EvalTask` dataclass — callers define their own instances.
``rubrics``
    :class:`ScoringBand`, :class:`RubricDimension`, :class:`RubricSpec` types.
``judge``
    :class:`JudgeClient` with pluggable :class:`JudgePrompt` template.
``harness``
    :class:`SkillEvalHarness` — the infrastructure orchestrator.
``example_tasks``
    Reference implementations of the three standard Jovaltus tasks.
``example_rubrics``
    Reference implementations of scoring rubrics for those tasks.
"""

from .config import EvalConfig, ModelConfig, load_config
from .harness import AgentRunResult, EvalReport, ProfileSpec, SkillEvalHarness
from .judge import JudgeClient, JudgePrompt, JudgeReport, calibrate
from .rubrics import RubricDimension, RubricSpec, ScoringBand
from .tasks import EvalTask

__all__ = [
    # Config
    "EvalConfig",
    "ModelConfig",
    "load_config",
    # Task types
    "EvalTask",
    # Rubric types
    "RubricSpec",
    "RubricDimension",
    "ScoringBand",
    # Judge
    "JudgeClient",
    "JudgePrompt",
    "JudgeReport",
    "calibrate",
    # Harness
    "SkillEvalHarness",
    "AgentRunResult",
    "EvalReport",
    "ProfileSpec",
]
