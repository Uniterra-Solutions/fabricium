# Setup

## Prerequisites

| Requirement | Version | Check |
|-------------|---------|-------|
| Python | ≥ 3.10 | `python --version` |
| uv | latest | `uv --version` |
| Git | any | For `git_utils` module (optional) |
| Docker | any | For `fabricium.testing` and `fabricium.evals` (optional) |

## Install (development)

```bash
git clone https://github.com/LaiTszKin/fabricium.git
cd fabricium
uv sync --dev
```

## Verify Installation

```bash
uv run pytest          # 104 tests
uv run ruff check .    # Lint
uv run mypy            # Type check
```

Run a single test file:

```bash
uv run pytest tests/test_skills.py -v
uv run pytest tests/test_plugin.py -v
```

Run only unit tests (skip Docker integration):

```bash
uv run pytest tests/ -v --ignore=tests/integration
```

## Install (as a dependency)

```bash
pip install fabricium
```

Or in a plugin's `pyproject.toml`:

```toml
[project]
dependencies = ["fabricium"]
```

Fabricium itself has **zero runtime dependencies** — only the Python standard library.

## Environment Variables

No required env vars for core fabricium usage.

| Variable | Required By | Description |
|----------|-------------|-------------|
| `HERMES_HOME` | Runtime | Hermes home directory. Auto-detected if unset. |
| `FABRICIUM_TEST_PROVIDER` | `fabricium.testing` | Provider for test Hermes env (default: `deepseek`) |
| `FABRICIUM_TEST_MODEL` | `fabricium.testing` | Model for test Hermes env (default: `deepseek/deepseek-chat`) |
| `FABRICIUM_TEST_API_KEY` | `fabricium.testing` | API key for test env |
| `FABRICIUM_TEST_PLUGIN_NAME` | `fabricium.testing.fixtures` | Plugin CLI name for pytest fixtures |
| `FABRICIUM_TEST_PLUGIN_DIR` | `fabricium.testing.fixtures` | Plugin source dir for pytest fixtures |
| `EVAL_CANDIDATE_PROVIDER` | `fabricium.evals` | Provider for agent being evaluated |
| `EVAL_CANDIDATE_MODEL` | `fabricium.evals` | Model for agent being evaluated |
| `EVAL_CANDIDATE_API_KEY` | `fabricium.evals` | API key for candidate |
| `EVAL_JUDGE_PROVIDER` | `fabricium.evals` | Provider for LLM judge |
| `EVAL_JUDGE_MODEL` | `fabricium.evals` | Model for LLM judge |
| `EVAL_JUDGE_API_KEY` | `fabricium.evals` | API key for judge |
| `EVAL_JOVALTUS_PLUGIN_DIR` | `fabricium.evals` | Path to Jovaltus plugin source |

## Docker Setup (optional)

For integration tests and evaluation:

```bash
docker pull nousresearch/hermes-agent:latest
```

## Editable Install (plugin development)

When developing a plugin that depends on fabricium:

```bash
cd /path/to/fabricium
uv pip install -e .
```

## How to Update

- New prerequisite? → Add to prerequisites table.
- New env var? → Add to environment variables table.
- Install steps changed? → Update commands.
- New Docker dependency? → Update Docker setup.

## Find It Fast

```bash
uv run pytest --co       # List all tests without running
uv run ruff check . --show-fixes  # See what ruff would fix
grep "FABRICIUM\|EVAL_" tests/conftest.py  # All test env vars
```
