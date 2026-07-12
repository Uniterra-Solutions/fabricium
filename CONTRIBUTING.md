# Contributing to Fabricium

Thank you for your interest in contributing! Fabricium is the shared infrastructure for Hermes plugins — improvements here benefit every plugin in the ecosystem.

## Development Setup

```bash
# Clone and enter the repo
git clone https://github.com/LaiTszKin/fabricium.git
cd fabricium

# Install dev dependencies (pytest, ruff, mypy)
uv sync --dev

# Run the test suite (104 tests)
uv run pytest

# Lint and type-check
uv run ruff check .
uv run mypy
```

## Project Structure

```
fabricium/
├── src/fabricium/
│   ├── __init__.py          # HermesPlugin class
│   ├── git_utils.py         # Git subprocess wrappers
│   ├── state.py             # JSON state persistence
│   ├── skills.py            # Bundled skill lifecycle
│   ├── prompts.py           # TTY-aware prompts
│   ├── evals/               # Skill evaluation framework
│   │   ├── __init__.py
│   │   ├── config.py        # EvalConfig (env-var driven)
│   │   ├── harness.py       # SkillEvalHarness (Docker orchestrator)
│   │   ├── judge.py         # JudgeClient (LLM-as-Judge)
│   │   ├── tasks.py         # EvalTask dataclass
│   │   ├── rubrics.py       # RubricSpec, RubricDimension, ScoringBand
│   │   ├── runner.py        # CLI entry point
│   │   ├── proxy.py         # Reasoning-model SSE proxy
│   │   ├── example_tasks.py # Reference tasks for Jovaltus
│   │   └── example_rubrics.py
│   └── testing/             # Integration test environment
│       ├── __init__.py
│       ├── harness.py       # HermesDockerTestEnv
│       ├── fixtures.py      # Pytest fixtures
│       └── assertions.py    # CliAssert
├── tests/
│   ├── conftest.py
│   ├── test_plugin.py
│   ├── test_git_utils.py
│   ├── test_state.py
│   ├── test_skills.py
│   ├── test_assertions.py
│   └── integration/
│       ├── conftest.py
│       └── test_cli.py
└── pyproject.toml
```

## Coding Standards

### Python

- **Style:** [ruff](https://docs.astral.sh/ruff/) with rules `E`, `F`, `I`, `N`, `W` (line length 100)
- **Types:** [mypy](https://mypy-lang.org/) with `--strict`
- **Tests:** [pytest](https://docs.pytest.org/) — aim for coverage on new code
- **Formatting:** ruff handles import sorting and formatting

Before committing:

```bash
uv run ruff check .          # Must pass
uv run ruff format --check . # Must be clean
uv run mypy                  # Must pass with --strict
uv run pytest                # All 104 tests must pass
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

- feat(evals): add parallel task execution
- fix(state): handle empty profiles in load_state
- refactor(plugin): extract profile helpers
- docs(readme): add eval quick start
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `ci`.

## Pull Request Process

1. **Open an issue first** for significant changes — discuss the design before writing code
2. **Branch from `main`** — use a descriptive branch name (`feat/eval-parallel`, `fix/state-empty-profiles`)
3. **Keep PRs focused** — one logical change per PR. If you find a pre-existing issue, open a separate PR
4. **Include tests** — new features need tests; bug fixes should include a regression test
5. **Update docs** — if you add/change public API, update README.md
6. **All checks must pass** — ruff, mypy, and pytest are required

## Design Principles

When contributing, keep these in mind:

1. **Extract only what's actually shared.** Code goes into Fabricium only when at least two plugins need it.
2. **Convention over configuration.** Sensible defaults. 99% of plugins shouldn't need options.
3. **Library, not framework.** Plugins import Fabricium — Fabricium doesn't control them.
4. **Zero runtime dependencies.** Fabricium uses only the Python standard library at runtime.
5. **Backward compatibility.** Existing plugins must not break on upgrade.
6. **TTY-safe by default.** Interactive prompts fall back to safe defaults when stdin is not a TTY.

## Running Integration Tests

Integration tests require Docker and a Hermes agent image:

```bash
# Pull the Hermes image (one-time)
docker pull nousresearch/hermes-agent:latest

# Run integration tests
uv run pytest tests/integration/ -v

# Skip integration tests in CI where Docker isn't available
uv run pytest tests/ --ignore=tests/integration/
```

## Questions?

Open a [GitHub Discussion](https://github.com/LaiTszKin/fabricium/discussions) or file an issue. We're happy to help!
