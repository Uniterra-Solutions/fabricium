# Conventions

## Naming

| Scope | Convention | Example |
|-------|------------|---------|
| Modules/files | `snake_case` | `git_utils.py`, `test_plugin.py` |
| Classes | `PascalCase` | `HermesPlugin`, `SkillEvalHarness` |
| Functions/methods | `snake_case` | `load_state()`, `_ensure_profile()` |
| Private methods | `_leading_underscore` | `_setup_command()`, `_sync_installed_profiles()` |
| Constants | `UPPER_SNAKE` | `DOCKER_IMAGE`, `DEFAULT_JUDGE_PROMPT` |
| Test files | `test_<module>.py` | `test_skills.py`, `test_plugin.py` |
| Test classes | `Test<PascalCase>` | `TestIsSkillDir`, `TestInstallBundledSkills` |
| Test methods | `test_<behavior>` | `test_installs_skills_to_global_dir` |

## Imports

- Standard library first, then third-party, then local (ruff `I` rule enforces via isort).
- Absolute imports within fabricium: `from fabricium import skills`, not `from . import skills`.
- Public API re-exported in `__init__.py` with explicit `__all__`.

## Type Hints

- mypy `--strict` enforced. All functions have type annotations.
- Use `| None` instead of `Optional[...]` (Python 3.10+).
- TypedDicts for structured dict returns: `FetchResult`, `AheadBehind`, `PullResult`, `CommitResult`.
- `Any` only where truly dynamic (e.g. Hermes `ctx` parameter, JSON state).

## Error Handling

- Git operations: return typed dicts with `success: bool`, never raise.
- Docker operations: `_docker_ok()` helper raises `RuntimeError` with stdout/stderr context.
- State operations: catch `OSError` and print warnings; never crash.
- Subprocess calls: `CalledProcessError` caught and surfaced as structured results.

## CLI Output

- Unicode markers for UX: ✓ ✗ ⏭ 📁 📚 🧠 📦 🔍 ⚡ 📊 ✅ ⚠️ 🗑 🔄 📋
- Commands print to stdout directly (no logging framework for user output).
- `logger.info()` for debug/internal messages only.
- TTY detection: `sys.stdin.isatty()` — non-TTY uses safe defaults without blocking.
- Explicit `encoding="utf-8"` on all `Path.read_text()` / `Path.write_text()` / `subprocess.run(text=True)` calls. Prevents `UnicodeDecodeError` on Windows systems where the default locale encoding (e.g. cp950) cannot decode UTF-8 characters.

## State Management

- State file: `~/.hermes/<plugin>_state.json` (per-plugin, single file).
- State survives plugin updates.
- Schema: `{"profiles": {"<name>": {"soul_md": bool, "updated_at": "ISO-8601", "skills": [...]}}}`
- `_get_global_hermes_home()` resolves actual `~/.hermes/` even when `HERMES_HOME` points to a profile subdirectory.

## Git Conventions

- Conventional Commits: `feat:`, `fix:`, `test:`, `release:`.
- Changelog follows Keep a Changelog format.
- Release tags: `v<version>` (e.g. `v0.1.5`).
- PyPI publishing via OIDC Trusted Publishing (no API token).

## Testing Conventions

- Test framework: pytest.
- Fixture-based: `tmp_plugin_dir` creates a complete plugin tree with skills/ and SOUL.md.
- Integration tests: Docker-based, marked `@pytest.mark.integration`.
- Session-scoped Docker container for integration tests (not per-function).

## Security

- No secrets in code. API keys from environment variables.
- `.env` in `.gitignore` — never committed.
- Docker mounts fabricium source as read-only (`:ro`).

## How to Update

- Convention added/changed? → Update the relevant row above.
- New naming pattern? → Add to naming table.
- Linter rule changed? → Add to tool config first, then reflect here.

## Find It Fast

```bash
grep -rn "def _[a-z]" src/fabricium/ --include="*.py"  # Private methods
grep -rn "class Test" tests/ --include="*.py"            # Test classes
grep -r "TypedDict" src/fabricium/                       # TypedDict definitions
grep -r "prompt_yes_no" src/fabricium/                   # TTY prompt usage
```
