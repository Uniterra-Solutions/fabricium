# Module: Core (`fabricium.__init__`)

**Purpose:** `HermesPlugin` class — one-line plugin lifecycle registration for Hermes plugins.

**File:** `src/fabricium/__init__.py:36-733`

## Public API

| Symbol | Signature | Description |
|--------|-----------|-------------|
| `HermesPlugin` | `(name, plugin_dir, default_profile=None, soul_md_path="SOUL.md")` | Plugin lifecycle manager |
| `HermesPlugin.register(ctx)` | → `None` | Register CLI commands + bundled skills with Hermes |

## CLI Commands

| Command | Handler | Description |
|---------|---------|-------------|
| `hermes <name> setup` | `_setup_command()` | Interactive: create profile, install skills, deploy SOUL.md |
| `hermes <name> status` | `_status_command()` | Display per-profile installation state |
| `hermes <name> update` | `_update_pull()` | Update plugin (git or pip), refresh skills, sync profiles |
| `hermes <name> update --check` | `_update_check()` | Check for newer versions without applying |
| `hermes <name> update --git` | `_update_pull()` | Force git-based update (git pull) |
| `hermes <name> update --pip` | `_update_pull()` | Force pip-based update (pip install --upgrade) |

The `--check`, `--git`, and `--pip` flags can be combined (`--check` with `--git` or `--pip`).

## Update Mode Resolution

`_resolve_update_mode()` (`src/fabricium/__init__.py:413-424`) determines git vs pip:

| Condition | Mode |
|-----------|------|
| `--git` flag given | git |
| `--pip` flag given | pip |
| Auto-detect (neither flag given) | **pip** (preferred default) |

When auto-detected pip is unavailable (pip not found) and the user did not force `--pip`, the update falls back to git with a warning. `_update_check` also tries pip first and falls back to git when the package is not on PyPI.

All pip calls use `state._get_hermes_python()` instead of `sys.executable` to ensure `pip install` targets Hermes's managed Python environment, not the system Python (common issue on Windows).

## Profile Modes

| `default_profile` | Mode | Setup Behaviour |
|-------------------|------|-----------------|
| `"my-profile"` | Single-profile | Auto-uses named profile |
| `None` | Multi-profile | Lists all available profiles for interactive selection |

## Dependencies

**Inbound:** Every fabricium-using plugin imports `from fabricium import HermesPlugin`.

**Outbound:**
- `fabricium.skills` (`install_bundled_skills`, `get_bundled_skill_names`, `remove_stale_from_profile`)
- `fabricium.state` (`load_state`, `save_state`, `set_profile_state`, `_get_global_hermes_home`, `_get_hermes_python`)
- `fabricium.prompts` (`prompt_yes_no`)
- `fabricium.git_utils` (`is_git_repo`, `fetch_remote`, `pull_branch`, `get_ahead_behind`, `get_local_head`, `get_remote_url`)

## Patterns & Gotchas

- **State-based stale detection** (`src/fabricium/__init__.py:233-239`): Previous skills recorded in per-profile state. On update, `previous_skills - bundled_names = stale`. This avoids cross-touching other plugins' skills.
- **Dual git/pip update** (`src/fabricium/__init__.py:413-681`): `_resolve_update_mode()` defaults to pip (not git). Pip-installed plugins get `pip install --upgrade <name>` via `state._get_hermes_python()`; git is the fallback when pip is unavailable. `--git`/`--pip` flags override auto-detection.
- **Pip fallback to git** (`src/fabricium/__init__.py:528-536`): When auto-detected pip fails (pip not found) and the user did not force `--pip`, the update falls back to git with a warning.
- **Pip check via `--dry-run`** (`src/fabricium/__init__.py:490-512`): `_update_check_pip()` runs `pip install --dry-run --upgrade <name>` to check PyPI without installing.
- **Auto fabricium upgrade** (`src/fabricium/__init__.py:541-555`): Every `update` command runs `pip install --upgrade fabricium` so plugins always get the latest fabricium.
- **`_ensure_profile()`** (`src/fabricium/__init__.py:127-153`): Creates profile via `hermes profile create` subprocess. Falls back to manual instructions if `hermes` not on PATH.
- **TTY-safety throughout**: Non-interactive contexts (CI, cron, piped input) use safe defaults — no blocking prompts.

## See Also

- [Skills Module](skills.md) — bundled skill lifecycle details
- [State Module](state.md) — JSON persistence details
- [Git Utils Module](git-utils.md) — git subprocess wrappers

## How to Update

- New CLI command added? → Add to CLI commands table + update dispatch in `_dispatch()`.
- New profile mode? → Add row to profile modes table.
- Behaviour change in update/setup flow? → Update Patterns section.

## Find It Fast

```bash
grep -n "def _setup\|def _status\|def _update\|def _dispatch\|def _resolve_update_mode" src/fabricium/__init__.py
grep -n "class HermesPlugin" src/fabricium/__init__.py
```
