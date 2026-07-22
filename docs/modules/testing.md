# Module: Testing (`fabricium.testing`)

**Purpose:** Docker-based Hermes test environment for plugin integration testing. Provides container lifecycle, CLI execution, and composable output assertions.

**Files:** `src/fabricium/testing/harness.py`, `assertions.py`, `fixtures.py`

## Public API — Harness

| Class | Description |
|-------|-------------|
| `HermesDockerTestEnv` | Context manager: provision Docker container, mount plugin + fabricium, run CLI commands |
| `CliResult` | Dataclass: `exit_code`, `stdout`, `stderr`, `.success` property, `.contains(text)` |
| `HermesConfig` | Provider/model configuration from env vars |

### `HermesDockerTestEnv` API

| Method | Description |
|--------|-------------|
| `start(skip_fabricium_install=False)` | Pull image, create temp dir, launch container, install plugin + fabricium |
| `stop()` | Remove container, delete temp dir |
| `run_cli(*args, timeout=60)` | Execute `hermes <args>` inside container, return `CliResult` |
| `run_cli_json(*args, timeout=60)` | Like `run_cli` but parse stdout as JSON |
| `__enter__()` / `__exit__()` | Context manager — auto start/stop |

### Constructor Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `plugin_name` | (required) | Plugin's CLI namespace |
| `plugin_dir` | (required) | Plugin source directory |
| `fabricium_src` | `None` | Fabricium source tree (mounted for editable install) |
| `config` | `HermesConfig()` | Provider/model config from env |
| `image` | `"nousresearch/hermes-agent:latest"` | Docker image |
| `keep` | `False` | Don't tear down on exit (debugging) |

## Public API — Assertions

| Function | Description |
|----------|-------------|
| `assert_exit_code(result, expected=0)` | Exit code matches |
| `assert_stdout_contains(result, text)` | Text present in stdout |
| `assert_stdout_contains_any(result, texts)` | At least one text present |
| `assert_stdout_matches(result, pattern)` | Regex match in stdout |
| `assert_stdout_not_contains(result, text)` | Text absent from stdout |
| `assert_setup_completed(result, plugin_name="")` | Setup completion message |
| `assert_profile_created(result, profile_name)` | Profile created during setup |
| `assert_profile_ready(result, profile_name)` | Profile already existed |
| `assert_profile_in_output(result, profile_name)` | Profile mentioned anywhere |
| `assert_skills_installed(result)` | Skills installed message |
| `assert_soul_md_applied(result)` | SOUL.md deployed |
| `assert_soul_md_skipped(result)` | SOUL.md explicitly skipped |
| `assert_no_skills_installed(result)` | No skills installed |
| `assert_status_shows_profile(result, profile_name, with_soul_md=True)` | Status table entry |
| `assert_status_shows_no_profiles(result, plugin_name)` | No profiles installed |
| `assert_update_check_responded(result)` | Update check produced diagnostic (git or pip) |
| `assert_up_to_date(result, plugin_name="")` | Up-to-date message |
| `assert_behind_remote(result)` | Behind remote message |

All assertions also available as `CliAssert.<name>()` static methods.

## Public API — Fixtures

| Fixture | Scope | Description |
|---------|-------|-------------|
| `hermes_config` | session | `HermesConfig` from env vars |
| `hermes_test_env` | session | Yields `HermesDockerTestEnv` |

Requires env vars: `FABRICIUM_TEST_PLUGIN_NAME`, `FABRICIUM_TEST_PLUGIN_DIR`.

## Dependencies

**Inbound:** Plugin integration test suites (`tests/integration/test_cli.py`).

**Outbound:** Docker CLI (`subprocess.run(["docker", ...])`).

## Patterns & Gotchas

- **Src layout detection** (`harness.py:298-319`): `_install_plugin()` auto-detects `src/<name>/plugin.yaml` vs flat `plugin.yaml` layout. Falls back to creating minimal `plugin.yaml` if none found.
- **Read-only fabricium mount** (`harness.py:341`): `-v <src>:/opt/fabricium:ro` — prevents test side-effects from modifying the source tree.
- **`HERMES_DOCKER_EXEC_AS_ROOT`** (`harness.py:378`): Env var for root execution inside container (needed for `uv pip install`).
- **Diagnostic on assertion failure** (`assertions.py:67-78`): Every failed assertion includes stdout excerpt + stderr. No guessing.
- **Session-scoped Docker** (`fixtures.py:84`): Container created once per test session, not per function. Reduces test time dramatically.

## See Also

- [Evals Module](evals.md) — similar Docker patterns for evaluation
- [Architecture](../architecture.md#container-diagram-c4-level-2)

## How to Update

- New assertion? → Add function + delegate in `CliAssert`.
- Container lifecycle changed? → Update `start()` method doc.
- New fixture? → Add to fixtures table.

## Find It Fast

```bash
grep -n "def " src/fabricium/testing/harness.py          # All harness methods
grep -n "def assert_" src/fabricium/testing/assertions.py # All assertions
grep -rn "HermesDockerTestEnv" tests/                     # Test usage
```
