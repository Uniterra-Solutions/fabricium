# Module: State (`fabricium.state`)

**Purpose:** JSON state persistence for Hermes plugins. Reads/writes `~/.hermes/<plugin>_state.json`.

**File:** `src/fabricium/state.py`

## Public API

| Function | Signature | Description |
|----------|-----------|-------------|
| `_get_global_hermes_home()` | `() -> Path` | Resolve `~/.hermes/` even when `HERMES_HOME` points to a profile subdirectory |
| `get_state_path(plugin_name)` | `(str) -> Path` | Path to `~/.hermes/<plugin_name>_state.json` |
| `load_state(plugin_name)` | `(str) -> dict` | Load state dict. Returns `{"profiles": {}}` if file missing or corrupt |
| `save_state(plugin_name, state)` | `(str, dict) -> None` | Write state dict to JSON file. Creates parent dirs. Catches OSError gracefully |
| `set_profile_state(plugin_name, profile_name, soul_md)` | `(str, str, bool) -> None` | Record a profile setup with timestamp |

## State Schema

```json
{
  "profiles": {
    "<profile_name>": {
      "soul_md": true,
      "updated_at": "2026-07-12T15:30:00",
      "skills": ["skill-a", "skill-b"]
    }
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `profiles` | `dict[str, object]` | Per-profile installation records |
| `soul_md` | `bool` | Whether SOUL.md was deployed to this profile |
| `updated_at` | `str` (ISO-8601) | Last setup/update timestamp |
| `skills` | `list[str]` | Skill names recorded as installed (added by `_sync_installed_profiles`) |

## Dependencies

**Inbound:** `fabricium/__init__.py` (`HermesPlugin`).

**Outbound:** None (stdlib only: `json`, `os`, `datetime`, `pathlib`).

## Patterns & Gotchas

- **`_get_global_hermes_home()` resolution** (`src/fabricium/state.py:14-28`): When running under a profile, `HERMES_HOME` is set to `~/.hermes/profiles/<name>/`. This function detects the `profiles/` segment and walks up two levels to find the true global home. Without this, state files would be written to the wrong location.
- **Graceful degradation** (`src/fabricium/state.py:42-49`): `load_state` returns `{"profiles": {}}` on any read/parse failure — never crashes.
- **`save_state` swallows errors** (`src/fabricium/state.py:58-59`): Prints warning on `OSError` but does not propagate. Callers should not assume save succeeded.

## See Also

- [Core Module](core.md) — state usage in setup/status/update
- [Conventions](../conventions.md#state-management)

## How to Update

- State schema changed? → Update schema JSON + field table above.
- New field added? → Add to schema table and document which code populates it.
- Path resolution changed? → Update `_get_global_hermes_home()` section.

## Find It Fast

```bash
grep -rn "load_state\|save_state\|set_profile_state" src/fabricium/  # All callers
cat ~/.hermes/<plugin>_state.json | python -m json.tool               # Inspect real state
```
