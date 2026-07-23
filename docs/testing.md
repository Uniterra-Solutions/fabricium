# Testing

## Framework

| Component | Tool | Config |
|-----------|------|--------|
| Test runner | pytest | `pyproject.toml:[tool.pytest.ini_options]` |
| Test path | `tests/` | 104 tests total |
| Linter | ruff | Rules: E, F, I, N, W |
| Type checker | mypy | `--strict` mode |

## Running Tests

```bash
# Full suite
uv run pytest

# Single file
uv run pytest tests/test_skills.py -v

# Single test
uv run pytest tests/test_skills.py::TestIsSkillDir::test_returns_true_for_skill_dir -v

# Unit tests only (skip Docker)
uv run pytest tests/ -v --ignore=tests/integration

# Integration tests (requires Docker)
uv run pytest tests/integration/ -v

# With coverage
uv run pytest --cov=src/fabricium --cov-report=term-missing
```

## Test Layout

```
tests/
├── conftest.py              # Shared fixtures: tmp_plugin_dir, etc.
├── test_plugin.py           # HermesPlugin lifecycle unit tests
├── test_skills.py           # Skill discovery, install, stale cleanup
├── test_state.py            # JSON state persistence
├── test_git_utils.py        # Git subprocess wrappers
├── test_assertions.py       # CliAssert unit tests
└── integration/
    ├── conftest.py          # Docker test env fixture (session-scoped)
    ├── test_cli.py          # E2E CLI: setup, status, update, update --check
    └── test_plugin/         # Minimal plugin for integration tests
        └── __init__.py      # register() entry point
```

## Fixture Patterns

### Unit tests: `tmp_plugin_dir`

Created by `conftest.py` — a complete plugin tree with:
- `skills/skill-a/SKILL.md`, `skills/skill-b/SKILL.md`
- `SOUL.md`

Each test gets a fresh temp directory.

### Integration tests: session-scoped Docker

```python
# tests/integration/conftest.py
@pytest.fixture(scope="session")
def hermes_test_env():
    env = HermesDockerTestEnv(...)
    env.start()
    yield env
    env.stop()
```

Container created once per session — reused across all integration tests.

## Test Markers

| Marker | Description |
|--------|-------------|
| `integration` | Tests requiring Docker + Hermes image |
| `fabricium_plugin_name` | Override plugin name for integration tests |

Select/deselect:

```bash
uv run pytest -m "integration"          # Only integration
uv run pytest -m "not integration"      # Skip integration
```

## Hermes Desktop PYTHONPATH

When running tests inside the Hermes desktop app, the `PYTHONPATH` environment
variable includes Hermes's own venv site-packages
(`~/.hermes/hermes-agent/venv/lib/python3.11/site-packages`), which may contain
an older pip-installed copy of fabricium. This copy takes priority over the
project's editable install in Python's import resolution.

`tests/conftest.py` handles this automatically:

1. **Insert `src/` at `sys.path[0]`** — ensures the local source tree is searched
   before any PYTHONPATH or site-packages entry.
2. **Purge pre-loaded `fabricium` modules from `sys.modules`** — pytest or its
   plugins may import `fabricium` before conftest runs. Removing these cached
   modules forces a fresh import from the corrected `sys.path`.

No special command prefix is needed — `uv run pytest` works directly.

## Mock Policy

Fabricium tests use **minimal mocking**. The philosophy:

- Unit tests use temp directories and real filesystem operations — no `unittest.mock` for file I/O.
- Git tests use real git repos in temp directories (set up with `git init`).
- Docker tests use real Docker containers (marked `integration` — skipped in CI without Docker).
- Only mocking: environment variables via `monkeypatch` for path/state tests.

## CI Test Workflow

Not explicitly configured in the repo (no `.github/workflows/` detected). Recommended:

```yaml
# .github/workflows/test.yml
- run: uv sync --dev
- run: uv run pytest tests/ -v --ignore=tests/integration
- run: uv run ruff check .
- run: uv run mypy
```

Integration tests (Docker) require a Docker-capable runner.

## How to Update

- New test file? → Add to test layout tree.
- Test conventions changed? → Update fixture/mock sections.
- New marker? → Add to markers table + `pyproject.toml:[tool.pytest.ini_options].markers`.
- New test command? → Add to running tests section.

## Find It Fast

```bash
uv run pytest --markers                    # All registered markers
grep -r "def test_" tests/ --include="*.py" | wc -l  # Test count
grep -rn "@pytest.fixture" tests/conftest.py           # All fixtures
```
