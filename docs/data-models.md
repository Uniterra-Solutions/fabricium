# Data Models

Fabricium has no database. The data layer is a single JSON state file per plugin.

## State File Schema

**Location:** `~/.hermes/<plugin_name>_state.json`

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

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `profiles` | `object` | Yes | Map of profile name → profile state |
| `profiles.<name>.soul_md` | `bool` | Yes | Whether SOUL.md was deployed |
| `profiles.<name>.updated_at` | `string` (ISO-8601) | Yes | Last setup/update timestamp |
| `profiles.<name>.skills` | `array[string]` | No | Skill names recorded as installed (populated by `_sync_installed_profiles`) |

## State Lifecycle

```
setup ──► set_profile_state() ──► writes profiles.<name>
update ──► _sync_installed_profiles() ──► reads previous state, writes updated skills + timestamp
status ──► load_state() ──► reads profiles for display
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Single file per plugin | Simple, no database. Survives plugin updates. |
| JSON (not YAML/TOML) | `json` is stdlib. No parser dependency. |
| `_get_global_hermes_home()` resolution | State must live at `~/.hermes/` even when `HERMES_HOME` points to a profile subdirectory |
| Graceful degradation on read failure | `load_state()` returns `{"profiles": {}}` — never crashes |

See [State Module](modules/state.md) for the read/write API.

## How to Update

- New state field? → Add to schema table + update `set_profile_state()` / `_sync_installed_profiles()`.
- Schema version needed? → Add `"version": 1` to root and migration logic in `load_state()`.

## Find It Fast

```bash
python -c "import json; print(json.dumps(json.load(open('~/.hermes/<plugin>_state.json')), indent=2))"
grep -rn "profiles\[" src/fabricium/  # All state reads/writes
```
