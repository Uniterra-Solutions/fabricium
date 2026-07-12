# Fabricium

<p align="center">
  <strong>Shared Hermes Plugin Infrastructure</strong><br>
  <em>Build Hermes plugins in 5 minutes — focus on your unique tools, not plugin boilerplate.</em>
</p>

<p align="center">
  <a href="https://pypi.org/project/fabricium/"><img src="https://img.shields.io/pypi/v/fabricium?color=blue" alt="PyPI"></a>
  <a href="https://pypi.org/project/fabricium/"><img src="https://img.shields.io/pypi/pyversions/fabricium" alt="Python"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="License"></a>
</p>

---

**Fabricium** is the shared foundation for all [Hermes Agent](https://hermes-agent.nousresearch.com) plugins. It extracts the ~500 lines of lifecycle boilerplate that every Hermes plugin duplicates — CLI commands (`setup`, `status`, `update`), bundled skill management, Git self-update, and state persistence — into a single `HermesPlugin` class. Plugin authors write one line to register everything and focus on what makes their plugin unique.

Fabricium also provides a **Docker-based skill evaluation framework** (`fabricium.evals`) and a **Docker-based integration test environment** (`fabricium.testing`) so you can test and benchmark your plugins with real Hermes agent runs.

---

## Table of Contents

- [Installation](#installation)
- [Quick Start: Building a Plugin](#quick-start-building-a-plugin)
- [What Fabricium Provides](#what-fabricium-provides)
  - [CLI Commands (setup / status / update)](#cli-commands-setup--status--update)
  - [Profile Modes](#profile-modes)
  - [State Persistence](#state-persistence)
  - [Bundled Skill Lifecycle](#bundled-skill-lifecycle)
  - [Git Self-Update](#git-self-update)
- [Skill Evaluation Framework](#skill-evaluation-framework)
  - [Architecture](#evaluation-architecture)
  - [Quick Start: Running an Eval](#quick-start-running-an-eval)
  - [Defining Custom Tasks](#defining-custom-tasks)
  - [Defining Custom Rubrics](#defining-custom-rubrics)
  - [Judge Calibration](#judge-calibration)
- [Integration Test Environment](#integration-test-environment)
- [API Reference](#api-reference)
- [Design Philosophy](#design-philosophy)
- [Contributing](#contributing)
- [License](#license)

---

## Installation

```bash
pip install fabricium
```

Requires Python ≥ 3.10. Fabricium itself has **zero runtime dependencies** beyond the standard library.

---

## Quick Start: Building a Plugin

Here's a complete Hermes plugin built with Fabricium. The unique business logic — a single `hello` tool — is just 3 lines:

```python
# my_plugin/__init__.py
from pathlib import Path
from fabricium import HermesPlugin

plugin = HermesPlugin(
    name="hello-world",
    plugin_dir=Path(__file__).parent,
    default_profile="default",
)

def register(ctx):
    # One line registers setup/status/update CLI + bundled skills
    plugin.register(ctx)

    # Your unique tools — just business logic
    ctx.register_tool(
        name="hello",
        description="Say hello",
        handler=lambda args: print("Hello from my plugin!"),
    )
```

That's it. Users get:

```bash
$ hermes hello-world setup     # Install skills, deploy SOUL.md
$ hermes hello-world status    # Check installation state
$ hermes hello-world update    # Git pull + refresh skills
$ hermes hello-world update --check  # Check for updates
```

Bundled skills in `my_plugin/skills/` are auto-discovered and registered. A `SOUL.md` in the plugin root can be deployed as the agent's identity.

---

## What Fabricium Provides

### CLI Commands (setup / status / update)

| Command | Behaviour |
|---|---|
| `hermes <plugin> setup` | Interactive: create profile, install bundled skills, optionally deploy SOUL.md |
| `hermes <plugin> status` | Display per-profile installation state (skills, SOUL.md, last updated) |
| `hermes <plugin> update` | Git fetch + fast-forward pull, detect/remove stale skills, refresh installed skills, sync profiles |
| `hermes <plugin> update --check` | Compare local vs remote HEAD, report ahead/behind counts |

All commands are TTY-aware — in non-interactive contexts (CI, piped input), they use safe defaults without blocking.

### Profile Modes

| Mode | `default_profile` | Behavior |
|---|---|---|
| **Single-profile** | `"my-profile"` | Setup installs directly to the named profile. Status shows one row. |
| **Multi-profile** | `None` | Setup lists all available profiles for interactive selection. |

### State Persistence

Installation state is stored as JSON under `~/.hermes/<plugin>_state.json`. Each profile records:

- Whether skills are installed
- Whether SOUL.md was deployed
- Last update timestamp

The state file survives plugin updates and is used by `status` and `update` commands to track configuration across profiles.

### Bundled Skill Lifecycle

Skills placed in the plugin's `skills/` directory are:

- **Auto-discovered** — any subdirectory with a `SKILL.md` is registered
- **Installed globally** — copied to `~/.hermes/skills/` so all profiles can load them
- **Stale-detected** — on `update`, skills removed from the bundle are detected and offered for cleanup

### Git Self-Update

The `update` command uses `git pull --ff-only` on the plugin's source directory. Before pulling:

- Uncommitted changes are detected and the user is warned
- Remote refs are fetched and ahead/behind counts are displayed
- After pulling, stale skills are detected and removed, remaining skills are refreshed, and all profiles are synced

All git operations are exposed in `fabricium.git_utils` for direct use — fetch, pull, diff, commit, ancestor checks, and more.

---

## Skill Evaluation Framework

`fabricium.evals` provides a complete **LLM-as-Judge evaluation pipeline** for measuring how much a skill (like the Jovaltus pipeline) improves agent output quality. It follows the [SkillsBench](https://arxiv.org/abs/2503.12345) methodology: identical prompts, universal rubrics, and output-quality deltas between bare and skill-equipped profiles.

### Evaluation Architecture

```
┌─────────────────────────────────────────────────┐
│                 Eval Runner (CLI)               │
│         python -m fabricium.evals.runner        │
├─────────────────────────────────────────────────┤
│  SkillEvalHarness                               │
│  ├── Docker container lifecycle                 │
│  ├── Multi-profile setup (bare vs skill)        │
│  ├── Workspace init (git, seed files)           │
│  ├── Agent execution with trace capture         │
│  └── Result collection                          │
├─────────────────────────────────────────────────┤
│  JudgeClient                                    │
│  ├── Cross-provider judging (Anthropic/OpenAI)  │
│  ├── Position randomization                     │
│  ├── Structured JSON parsing                    │
│  └── Calibration (Cohen's κ, Spearman ρ)        │
└─────────────────────────────────────────────────┘
```

### Quick Start: Running an Eval

```bash
# Set required env vars
export EVAL_CANDIDATE_PROVIDER=deepseek
export EVAL_CANDIDATE_MODEL=deepseek/deepseek-chat
export EVAL_CANDIDATE_API_KEY=sk-...

export EVAL_JUDGE_PROVIDER=anthropic
export EVAL_JUDGE_MODEL=anthropic/claude-sonnet-4
export EVAL_JUDGE_API_KEY=sk-ant-...

export EVAL_JOVALTUS_PLUGIN_DIR=/path/to/jovaltus/plugin

# Run all tasks (3 runs per task per profile)
python -m fabricium.evals.runner

# Run a specific task
EVAL_TASKS=python-backend python -m fabricium.evals.runner
```

Reports are written as JSON to `eval_results/` (configurable via `EVAL_OUTPUT_DIR`):

```json
{
  "tasks": {
    "python-backend": {
      "runs": 12,
      "verdicts": [
        {"profile": "bare", "dimensions": {...}, "total": 65.0},
        {"profile": "jovaltus-agent", "dimensions": {...}, "total": 82.5}
      ]
    }
  },
  "skill_lift": {
    "python-backend": {
      "bare_score": 65.0,
      "skill_score": 82.5,
      "skill_lift": 17.5
    }
  }
}
```

### Defining Custom Tasks

```python
from fabricium.evals import EvalTask

task = EvalTask(
    id="my-task",
    name="My Custom Task",
    description="Tests whether the agent can build X",
    natural_prompt="Build a REST API with ...",      # without skill keywords
    explicit_prompt="Using the pipeline, build ...",  # with skill keywords
    seed_files={"pyproject.toml": "[project]\nname = ..."},
    workspace_subdir="my-task",
    verify_commands=[
        ("pytest", "cd /workspace/my-task && uv run pytest -v"),
    ],
)
```

### Defining Custom Rubrics

```python
from fabricium.evals import RubricSpec, RubricDimension, ScoringBand

rubric = RubricSpec(
    task_id="my-task",
    dimensions=[
        RubricDimension(
            id="functional_correctness",
            label="Functional Correctness",
            weight=0.40,
            description="Do all features work?",
            scoring_bands=[
                ScoringBand(10, "All features work. All tests pass."),
                ScoringBand(7, "Most features work. One bug."),
                ScoringBand(5, "Half the features work."),
                ScoringBand(3, "Basic scaffolding only."),
                ScoringBand(0, "No implementation."),
            ],
            evidence_hints=["Run tests", "Check file tree"],
        ),
    ],
)
```

### Judge Calibration

```python
from fabricium.evals import calibrate

human_labels = [
    {"task_id": "my-task", "dimension": "functional_correctness", "score": 7},
    {"task_id": "my-task", "dimension": "code_cleanliness", "score": 8},
]

metrics = calibrate(human_labels, judge_reports)
# {"agreement_pct": 85.0, "cohens_kappa": 0.72, "spearman_rho": 0.88, "n_pairs": 50}
```

---

## Integration Test Environment

`fabricium.testing` provides a **Docker-based Hermes test environment** for integration testing plugins:

```python
from pathlib import Path
from fabricium.testing import HermesDockerTestEnv, CliAssert

env = HermesDockerTestEnv(
    plugin_name="my-plugin",
    plugin_dir=Path(__file__).parent.parent,
    fabricium_src=Path("/path/to/fabricium"),
)

with env:
    # Run CLI commands and assert output
    result = env.run_cli("my-plugin", "setup")
    assert result.success

    result = env.run_cli("my-plugin", "status")
    CliAssert(result).contains("Skills + SOUL.md ✓")
```

Key features:
- **Disposable containers** — each test gets a clean Hermes environment
- **TTY-safe** — non-interactive by default, suitable for CI
- **Plugin auto-detection** — copies your plugin source into the container
- **Fabricium mount** — mounts the fabricium source tree for editable installs

---

## API Reference

### `fabricium.HermesPlugin`

```python
HermesPlugin(
    name: str,                          # Plugin name (CLI namespace, state file)
    plugin_dir: Path,                   # Plugin root directory
    default_profile: str | None = None, # None = multi-profile mode
    soul_md_path: str = "SOUL.md",      # Relative to plugin_dir
)
```

**Key methods:**

| Method | Description |
|---|---|
| `register(ctx)` | Register CLI commands + bundled skills with Hermes |

### `fabricium.evals`

| Class | Description |
|---|---|
| `SkillEvalHarness` | Docker-based evaluation orchestrator |
| `JudgeClient` | LLM-as-Judge with cross-provider support |
| `EvalConfig` | Environment-variable-driven configuration |
| `EvalTask` | Task definition (prompts, seed files, verify commands) |
| `RubricSpec` / `RubricDimension` / `ScoringBand` | Rubric building blocks |
| `JudgePrompt` | Customizable judge prompt template |
| `calibrate()` | Judge-human agreement metrics |

### `fabricium.testing`

| Class | Description |
|---|---|
| `HermesDockerTestEnv` | Docker-based Hermes test environment |
| `CliAssert` | Composable CLI output assertions |
| `HermesConfig` | Provider/model configuration for test env |

### `fabricium.git_utils`

Git subprocess wrappers: `fetch_remote()`, `pull_branch()`, `get_ahead_behind()`, `get_diff()`, `get_diff_stat()`, `is_ancestor()`, `stage_all()`, `commit()`, and more.

### `fabricium.state`

JSON state persistence: `load_state()`, `save_state()`, `set_profile_state()`.

### `fabricium.skills`

Bundled skill lifecycle: `install_bundled_skills()`, `remove_stale_skills()`, `get_bundled_skill_names()`.

### `fabricium.prompts`

TTY-aware prompts: `prompt_yes_no()`.

---

## Design Philosophy

1. **Extract only what's actually shared.** Fabricium contains code that both Caelterra and Jovaltus duplicated. No speculative abstractions for "future" needs.

2. **Convention over configuration.** Sensible defaults (single profile, standard paths). 99% of plugins need zero configuration.

3. **Library, not framework.** Plugins import Fabricium — Fabricium doesn't control plugins. Any behavior can be bypassed or replaced.

4. **Backward-compatible migration.** Plugins migrating to Fabricium keep the same CLI behavior, state file format, and user experience.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding standards, and pull request guidelines.

Quick start for development:

```bash
git clone https://github.com/LaiTszKin/fabricium.git
cd fabricium
uv sync --dev
uv run pytest          # 104 tests
uv run ruff check .    # lint
uv run mypy            # type check
```

---

## License

MIT — see [LICENSE](LICENSE).

---

<p align="center">
  <em>Fabricium — from Latin <strong>fabrica</strong> (workshop, forge). The foundation every Hermes plugin stands on.</em>
</p>
