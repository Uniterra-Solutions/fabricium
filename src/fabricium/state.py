"""JSON state persistence for Hermes plugins.

Provides load/save helpers for per-plugin state files stored under
~/.hermes/<plugin>_state.json.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any


def _get_global_hermes_home() -> Path:
    """Return the global Hermes home directory, not a profile-specific one.

    When running under a profile, HERMES_HOME is set to the profile directory
    (e.g. ~/.hermes/profiles/<name>/). We need the actual global home
    (~/.hermes/) for the state file, skills, profiles dir, etc.
    """
    env_home = os.environ.get("HERMES_HOME")
    if env_home:
        p = Path(env_home).resolve()
        # If we're under a profiles/<name> directory, go up two levels
        if len(p.parts) >= 2 and p.parts[-2] == "profiles":
            return p.parent.parent
        return p
    return Path.home() / ".hermes"


def get_state_path(plugin_name: str) -> Path:
    """Return the path to the plugin's state file.

    Example: ~/.hermes/caelterra_state.json
    """
    return _get_global_hermes_home() / f"{plugin_name}_state.json"


def load_state(plugin_name: str) -> dict[str, Any]:
    """Load installation state from JSON file."""
    state_path = get_state_path(plugin_name)
    if state_path.exists():
        try:
            result = json.loads(state_path.read_text())
            assert isinstance(result, dict)
            return result
        except (json.JSONDecodeError, OSError, AssertionError):
            pass
    return {"profiles": {}}


def save_state(plugin_name: str, state: dict[str, Any]) -> None:
    """Save installation state to JSON file."""
    state_path = get_state_path(plugin_name)
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")
    except OSError as e:
        print(f"  ! Could not save state: {e}")


def set_profile_state(plugin_name: str, profile_name: str, soul_md: bool) -> None:
    """Record that a profile has been set up.

    The presence of a profile in the state means skills have been installed.
    The *soul_md* flag indicates whether SOUL.md was also deployed.
    """
    state = load_state(plugin_name)
    state["profiles"][profile_name] = {
        "soul_md": soul_md,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    save_state(plugin_name, state)
