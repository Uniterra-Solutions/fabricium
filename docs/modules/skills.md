# Module: Skills (`fabricium.skills`)

**Purpose:** Bundled skill lifecycle — discovery, installation, and stale-cleanup of skills shipped inside a plugin's `skills/` directory.

**File:** `src/fabricium/skills.py`

## Public API

| Function | Signature | Description |
|----------|-----------|-------------|
| `is_skill_dir(path)` | `(Path) -> bool` | True if directory contains `SKILL.md` |
| `get_bundled_skill_names(plugin_dir)` | `(Path) -> set[str]` | Skill names bundled in `plugin_dir/skills/` |
| `install_bundled_skills(plugin_dir, target_dir=None)` | `(Path, Path?) -> bool` | Copy all bundled skills to target. Default target: `~/.hermes/skills/` |
| `remove_stale_from_profile(profile_skills_dir, stale)` | `(Path, set[str]) -> None` | Remove skills no longer in bundle (state-based, safe) |
| `remove_stale_skills(plugin_dir, after_skills, target_dir=None)` | `(Path, set[str], Path?) -> None` | **Legacy.** Scans target dir for stale skills. Can cross-touch other plugins. Prefer `remove_stale_from_profile`. |

## Skill Directory Layout

```
plugin_dir/skills/
├── skill-a/
│   ├── SKILL.md         # Required — YAML frontmatter + markdown
│   ├── references/      # Optional — supporting docs
│   ├── scripts/         # Optional — executable scripts
│   └── templates/       # Optional — template files
└── skill-b/
    └── SKILL.md
```

## Installation Target

`install_bundled_skills` uses `shutil.copytree(child, dst, dirs_exist_ok=True)` — the entire skill directory is copied, including `references/`, `scripts/`, `templates/`, and any other auxiliary files.

## Dependencies

**Inbound:** `fabricium/__init__.py` (`HermesPlugin`), plugin tests.

**Outbound:**
- `fabricium.prompts` (`prompt_yes_no`) — used for stale-skill removal confirmation
- `fabricium.state` (`_get_global_hermes_home`) — resolved home for default install target

## Patterns & Gotchas

- **State-based vs legacy stale detection** (`src/fabricium/skills.py:29-51` vs `67-89`): Legacy `remove_stale_skills` scans the target directory and flags anything not in `after_skills` as stale. This is dangerous when the target dir is shared (e.g. `~/.hermes/skills/` for the `default` profile) — it can remove other plugins' skills. Prefer `remove_stale_from_profile` with an explicit stale set derived from per-profile state.
- **Idempotent install** (`src/fabricium/skills.py:116`): `copytree(..., dirs_exist_ok=True)` — re-running install overwrites existing files but doesn't fail on existing directories.
- **Silently skips non-skill dirs** (`src/fabricium/skills.py:110-111`): Directories without `SKILL.md` are ignored.

## See Also

- [Core Module](core.md) — where skills are installed during setup/update
- [Conventions](../conventions.md#state-management) — per-profile state format

## How to Update

- New skill lifecycle function? → Add to public API table.
- Installation logic changed? → Update installation target section.
- Legacy function deprecated? → Mark in table and add migration note.

## Find It Fast

```bash
grep -n "def " src/fabricium/skills.py
grep -rn "install_bundled_skills\|remove_stale" src/fabricium/  # All callers
```
