"""JSON state persistence for Hermes plugins.

Provides load/save helpers for per-plugin state files stored under
~/.hermes/<plugin>_state.json.
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Module-level cache for CLI-resolved Hermes home.
# Set once per process to avoid repeated subprocess calls.
_HERMES_HOME_CACHE: Path | None = None


def _derive_global_home_from_config_path(config_path: Path) -> Path:
    """Derive the global Hermes home from a config.yaml path.

    If *config_path* is under ``profiles/<name>/config.yaml``, the
    global home is two levels up.  Otherwise the global home is the
    directory containing *config_path*.
    """
    parent = config_path.parent
    if len(parent.parts) >= 2 and parent.parts[-2] == "profiles":
        return parent.parent.parent
    return parent


def _resolve_hermes_home_via_cli() -> Path | None:
    """Try to determine the global Hermes home via the ``hermes`` CLI.

    Runs ``hermes config path`` to get the config file location, then
    derives the global home from it.  Returns ``None`` when the CLI is
    unavailable or fails.
    """
    try:
        result = subprocess.run(
            ["hermes", "config", "path"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=5,
        )
        if result.returncode == 0:
            config_path = Path(result.stdout.strip()).resolve()
            return _derive_global_home_from_config_path(config_path)
    except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError):
        pass
    return None


def _get_global_hermes_home() -> Path:
    """Return the global Hermes home directory, not a profile-specific one.

    Resolution order:
      1. ``HERMES_HOME`` environment variable (fast, always preferred).
      2. ``hermes config path`` CLI (cross-platform, no hardcoded paths).
      3. ``Path.home() / ".hermes"`` (Unix/macOS fallback).

    The result is cached at module level so the CLI is called at most
    once per process.
    """
    global _HERMES_HOME_CACHE

    # 1. Environment variable — no caching needed, authoritative.
    env_home = os.environ.get("HERMES_HOME")
    if env_home:
        p = Path(env_home).resolve()
        # If we're under a profiles/<name> directory, go up two levels
        if len(p.parts) >= 2 and p.parts[-2] == "profiles":
            return p.parent.parent
        return p

    # 2. Cached result from previous resolutions.
    if _HERMES_HOME_CACHE is not None:
        return _HERMES_HOME_CACHE

    # 3. Dynamic CLI resolution (cross-platform).
    cli_home = _resolve_hermes_home_via_cli()
    if cli_home is not None:
        _HERMES_HOME_CACHE = cli_home
        return cli_home

    # 4. Fallback — Unix/macOS convention.
    fallback = Path.home() / ".hermes"
    _HERMES_HOME_CACHE = fallback
    return fallback


def _get_hermes_python() -> str:
    """Return the Hermes-managed Python executable path.

    Uses the global Hermes home to locate ``.venv/bin/python3``
    (or ``.venv/Scripts/python.exe`` on Windows).  When the
    platform-specific entry point is missing, falls back to
    ``python`` inside the same directory before giving up and
    returning ``sys.executable``.

    This prevents ``pip install`` from targeting the system Python
    (common on Windows where ``sys.executable`` may point to a
    separately-installed system interpreter).
    """
    hermes_home = _get_global_hermes_home()
    if sys.platform == "win32":
        candidates = [
            hermes_home / ".venv" / "Scripts" / "python.exe",
            hermes_home / ".venv" / "Scripts" / "python",
        ]
    else:
        candidates = [
            hermes_home / ".venv" / "bin" / "python3",
            hermes_home / ".venv" / "bin" / "python",
        ]
    for python in candidates:
        if python.exists():
            return str(python)
    return sys.executable


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
            result = json.loads(state_path.read_text(encoding="utf-8"))
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
        state_path.write_text(
            json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
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
