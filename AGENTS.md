# Fabricium — Shared Hermes plugin infrastructure library

## Build & Test

```bash
# Full test suite (unit only — skips Docker integration tests)
uv run pytest tests/ -v --ignore=tests/integration

# Single test file
uv run pytest tests/test_skills.py -v

# Single test
uv run pytest tests/test_skills.py::TestIsSkillDir::test_returns_true_for_skill_dir -v

# Integration tests (requires Docker)
uv run pytest tests/integration/ -v

# Lint
uv run ruff check .

# Format
uv run ruff format --check .

# Type check
uv run mypy
```

Run `uv sync --dev` once after cloning to install dev dependencies into `.venv/`.

## Tech Stack

- **Language**: Python ≥ 3.10 (target 3.10 floor)
- **Package manager**: `uv` — lockfile at `uv.lock`
- **Build system**: hatchling (`pyproject.toml`, src layout)
- **Testing**: pytest ≥ 8 (104 tests, `tests/` directory)
- **Lint/Format**: ruff ≥ 0.8 (rules E, F, I, N, W; line-length 100)
- **Type check**: mypy ≥ 1.16 (`--strict` mode on `src/fabricium`)
- **Runtime deps**: None — pure Python standard library

## Project Structure

| Directory | Responsibility |
|---|---|
| `src/fabricium/` | Core library: `HermesPlugin` lifecycle, state, git, skills, prompts |
| `src/fabricium/testing/` | Docker-based integration test harness (`HermesDockerTestEnv`) |
| `src/fabricium/evals/` | LLM-as-Judge skill evaluation pipeline (`SkillEvalHarness`) |
| `tests/` | Unit tests — real filesystem, real git repos in temp dirs |
| `tests/integration/` | Docker-based E2E CLI tests (session-scoped container) |
| `docs/` | Architecture, conventions, testing guides — not task instructions |

`src/fabricium/__init__.py` contains the `HermesPlugin` class (~600 lines) — the primary entry point.

## Key Constraints

- **Zero runtime dependencies.** All subprocess/HTTP via stdlib (`subprocess.run`, `urllib.request`). Adding a dependency is a major architectural decision.
- **Git operations return typed dicts, never raise.** `FetchResult`, `AheadBehind`, `PullResult`, `CommitResult` all have `success: bool`. Catch `CalledProcessError` internally.
- **Absolute imports within fabricium.** Use `from fabricium import skills`, not `from . import skills`.
- **TTY-aware prompts.** `sys.stdin.isatty()` gates all interactive prompts — non-TTY runs must use safe defaults without blocking.
- **State files survive plugin updates.** JSON at `~/.hermes/<plugin>_state.json`. Schema: `{"profiles": {"<name>": {...}}}`. Use `_get_global_hermes_home()` to resolve the real `~/.hermes/` when `HERMES_HOME` points to a profile subdir.
- **Plugin distribution: pip entry point + src layout.** Flat `packages = ["."]` breaks editable installs. Always use `packages = ["src/<name>"]`.

## Testing

- Test files mirror source: `tests/test_<module>.py` per `src/fabricium/<module>.py`.
- **Minimal mocking.** Unit tests use real temp directories and real `git init` repos — no `unittest.mock` for filesystem or subprocess. Only `monkeypatch` for env vars.
- Integration tests use a real Docker container with `nousresearch/hermes-agent:latest`, marked `@pytest.mark.integration`.
- `tests/conftest.py` provides shared fixtures (`tmp_plugin_dir` creates a complete plugin tree with skills/ and SOUL.md).
- Docker mounts fabricium source as read-only (`:ro`).

## Git Workflow

- **Conventional Commits**: `feat:`, `fix:`, `test:`, `release:`.
- **Release tags**: `v<version>` (e.g. `v0.1.5`).
- **PyPI publishing**: OIDC Trusted Publishing (GitHub Actions → PyPI, no API token).
- **Changelog**: Keep a Changelog format in `CHANGELOG.md`.

## Documentation

- `docs/architecture.md` — system context, container diagrams, data flows, key decisions
- `docs/conventions.md` — naming, imports, types, error handling, state schema, security
- `docs/testing.md` — test commands, fixture patterns, mock policy, markers
- `docs/tech-stack.md` — full version table, runtime deps rationale, external services
- `docs/project-structure.md` — directory tree, responsibility table
- `docs/modules/` — per-module deep dives for `core`, `skills`, `state`, `git-utils`, `testing`, `evals`

## Boundaries

**Always:**
- Run tests before committing (`uv run pytest tests/ -v --ignore=tests/integration`)
- Add tests for new code
- Match existing conventions in `docs/conventions.md`

**Ask first:**
- Adding a runtime dependency (breaks the zero-deps contract)
- Changing the state file schema (affects all downstream plugins)
- Modifying the `HermesPlugin` public API
- Bumping the Python version floor

**Never:**
- Commit `.env` files or secrets
- Use relative imports inside `src/fabricium/`
- Raise exceptions from git operations — use `success: bool` return dicts
- Modify `tests/integration/test_plugin/` (it's a controlled test fixture)
