"""CLI entry point for skill evaluation.

Usage::

    # Set required env vars, then:
    python -m fabricium.evals.runner

    # Or filter specific tasks:
    EVAL_TASKS=python-backend python -m fabricium.evals.runner
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

from .config import load_config
from .example_rubrics import get_jovaltus_rubric
from .example_tasks import JOVALTUS_TASKS
from .harness import SkillEvalHarness


def main() -> None:
    """Run the full evaluation pipeline and write a JSON report."""
    logging.basicConfig(level=logging.INFO, format="%(name)s %(message)s")
    config = load_config()

    # ── Select tasks ──────────────────────────────────────────────
    task_ids: set[str]
    if "all" in config.tasks:
        task_ids = {t.id for t in JOVALTUS_TASKS}
    else:
        task_ids = set(config.tasks)

    tasks = [t for t in JOVALTUS_TASKS if t.id in task_ids]
    if not tasks:
        print(f"No tasks matched {config.tasks!r}. Available: {[t.id for t in JOVALTUS_TASKS]}")
        sys.exit(1)

    # ── Build harness ─────────────────────────────────────────────
    harness = SkillEvalHarness(config)
    harness.add_profile("bare")
    harness.add_profile(
        "jovaltus-agent",
        setup_commands=["hermes jovaltus setup"],
    )

    # ── Run each task ─────────────────────────────────────────────
    out_dir = Path("eval_results")
    out_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for task in tasks:
        print(f"\n{'=' * 60}")
        print(f"Task: {task.name} ({task.id})")
        print(f"{'=' * 60}")

        try:
            rubric = get_jovaltus_rubric(task.id)
        except KeyError:
            print(f"  No rubric for '{task.id}' — skipping")
            continue

        try:
            report = harness.run([task], rubric)
        except Exception as exc:
            print(f"  ERROR during eval: {exc}")
            import traceback

            traceback.print_exc()
            continue

        path = out_dir / f"report_{task.id}_{timestamp}.json"
        report.to_json(str(path))
        print(f"\n  Report written: {path}")

        # Print a quick summary
        lift = report.skill_lift.get(task.id, {})
        if "skill_lift" in lift:
            print(f"  Skill Lift: {lift['skill_lift']:.1f}")
            print(f"    bare:     {lift.get('bare_score', '?')}")
            print(f"    jovaltus: {lift.get('skill_score', '?')}")

    print(f"\n{'=' * 60}")
    print("Done. Reports in eval_results/")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
