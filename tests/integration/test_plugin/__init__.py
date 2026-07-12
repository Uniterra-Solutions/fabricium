"""A minimal Hermes plugin that imports fabricium.

This plugin exists SOLELY for fabricium's own integration tests.
It registers via :class:`fabricium.HermesPlugin` and adds no extra tools.
"""

import subprocess
import sys
from pathlib import Path


# Self-bootstrap: fabricium must be importable before the plugin can register
# CLI commands.  Hermes manages its own venv and may recreate it during updates,
# dropping plugin-only dependencies.  This guard ensures fabricium is installed
# on first import after a Hermes update without requiring a manual pip install.
def _ensure_fabricium() -> None:
    try:
        import fabricium  # noqa: F401
    except ImportError:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "fabricium"],
            check=True,
            capture_output=True,
        )
        # Clear stale import cache from the failed attempt above
        sys.modules.pop("fabricium", None)


_ensure_fabricium()

from fabricium import HermesPlugin  # noqa: E402  (must bootstrap fabricium first)

plugin = HermesPlugin(
    name="fabricium-test-plugin",
    plugin_dir=Path(__file__).parent,
)


def register(ctx):  # noqa: D103  (Hermes convention)
    plugin.register(ctx)
