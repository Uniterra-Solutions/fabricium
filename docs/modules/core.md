# Module: Core (`fabricium.__init__`)

**Purpose:** `HermesPlugin` class — one-line plugin lifecycle registration for Hermes plugins.

**File:** `src/fabricium/__init__.py:43-621`

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
| `hermes <name> update` | `_update_pull()` | Git pull + refresh skills + sync profiles |
| `hermes <name> update --check` | `_update_check()` | Compare local vs remote HEAD without pulling |

## Profile Modes

| `default_profile` | Mode | Setup Behaviour |
|-------------------|------|-----------------|
| `"my-profile"` | Single-profile | Auto-uses named profile |
| `None` | Multi-profile | Lists all available profiles for interactive selection |

## Dependencies

**Inbound:** Every fabricium-using plugin imports `from fabricium import HermesPlugin`.

**Outbound:**
- `fabricium.skills` (`install_bundled_skills`, `get_bundled_skill_names`, `remove_stale_from_profile`)
- `fabricium.state` (`load_state`, `save_state`, `set_profile_state`, `_get_global_hermes_home`)
- `fabricium.prompts` (`prompt_yes_no`)
- `fabricium.git_utils` (`is_git_repo`, `fetch_remote`, `pull_branch`, `get_ahead_behind`, `get_local_head`, `get_remote_url`)

## Patterns & Gotchas

- **State-based stale detection** (`src/fabricium/__init__.py:240-247`): Previous skills recorded in per-profile state. On update, `previous_skills - bundled_names = stale`. This avoids cross-touching other plugins' skills.
- **Graceful pip fallback** (`src/fabricium/__init__.py:428-434`): If plugin dir is not a git repo, update prints `pip install --upgrade` instructions instead of failing.
- **Auto fabricium upgrade** (`src/fabricium/__init__.py:536-550`): Every `update` command runs `pip install --upgrade fabricium` so plugins always get the latest fabricium.
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
grep -n "def _setup\|def _status\|def _update\|def _dispatch" src/fabricium/__init__.py
grep -n "class HermesPlugin" src/fabricium/__init__.py
```
