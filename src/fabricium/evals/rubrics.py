"""Rubric types for skill evaluation.

Provides :class:`ScoringBand`, :class:`RubricDimension`, and
:class:`RubricSpec` — the building blocks callers use to define
their own scoring rubrics.  fabricium does not ship with built-in
rubrics; every evaluation must supply its own.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScoringBand:
    """One discrete score level with concrete, verifiable criteria."""

    score: int
    criteria: str


@dataclass
class RubricDimension:
    """A single evaluation dimension with weighted scoring bands.

    Attributes
    ----------
    id:
        Machine-readable dimension id (e.g. ``"functional_completeness"``).
    label:
        Human-readable name (e.g. ``"Functional Completeness"``).
    weight:
        Proportion of the total score this dimension contributes
        (all weights should sum to 1.0).
    description:
        What this dimension measures in plain language.
    scoring_bands:
        Ordered list of discrete score levels.  Judges must pick the
        closest-matching band — no interpolation.
    evidence_hints:
        Hints for the judge on where to find evidence for this dimension.
    universal:
        If ``True`` (default), scored for both bare and skill-equipped
        profiles.  If ``False``, only scored for the skill-equipped profile
        (e.g. pipeline-specific dimensions).
    """

    id: str
    label: str
    weight: float
    description: str = ""
    scoring_bands: list[ScoringBand] = field(default_factory=list)
    evidence_hints: list[str] = field(default_factory=list)
    universal: bool = True


@dataclass
class RubricSpec:
    """A complete scoring rubric for one task.

    Callers define their own :class:`RubricSpec` instances and pass them
    to :class:`~fabricium.evals.harness.SkillEvalHarness`.
    """

    task_id: str
    dimensions: list[RubricDimension]

    @property
    def universal_dimensions(self) -> list[RubricDimension]:
        return [d for d in self.dimensions if d.universal]

    @property
    def jovaltus_dimensions(self) -> list[RubricDimension]:
        return [d for d in self.dimensions if not d.universal]

    def to_judge_json(self) -> dict[str, Any]:
        """Serialize rubric for injection into the judge prompt."""
        return {
            "task_id": self.task_id,
            "dimensions": [
                {
                    "id": d.id,
                    "label": d.label,
                    "weight": d.weight,
                    "description": d.description,
                    "scoring_bands": [
                        {"score": b.score, "criteria": b.criteria} for b in d.scoring_bands
                    ],
                    "evidence_hints": d.evidence_hints,
                    "applies_to": "both" if d.universal else "jovaltus_only",
                }
                for d in self.dimensions
            ],
        }
