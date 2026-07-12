"""Task definition types for skill evaluation.

Provides the :class:`EvalTask` dataclass that callers use to define
their own evaluation tasks.  fabricium handles the infrastructure
(container setup, agent execution, trace capture); the caller owns
the task content — prompts, seed files, verification commands.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EvalTask:
    """A single evaluation task defined by the caller.

    Attributes
    ----------
    id:
        Unique task identifier (e.g. ``"python-backend"``).
    name:
        Human-readable name.
    description:
        One-line summary of what the task tests.
    natural_prompt:
        The prompt WITHOUT any pipeline/skill keywords.
        Used to test whether the agent discovers the skill on its own.
    explicit_prompt:
        The prompt WITH explicit pipeline/skill activation keywords.
        Used to test pipeline execution when the skill is explicitly invoked.
    seed_files:
        Files to create in the workspace before the agent runs.
        Keys are paths relative to the workspace subdirectory,
        values are file contents.
    workspace_subdir:
        Subdirectory under the workspace base where the task runs.
    verify_commands:
        Shell commands to run after the agent completes to verify
        correctness.  Each tuple is ``(description, command)``.
    """

    id: str
    name: str
    description: str = ""
    natural_prompt: str = ""
    explicit_prompt: str = ""
    seed_files: dict[str, str] = field(default_factory=dict)
    workspace_subdir: str = ""
    verify_commands: list[tuple[str, str]] = field(default_factory=list)
