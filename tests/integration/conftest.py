"""Pytest configuration for fabricium integration tests.

Provides fixtures that manage a Docker-based Hermes environment
with the fabricium test plugin pre-installed.

IMPORTANT: set env vars BEFORE importing the fixtures — they're read at
import time by the session-scoped fixture.
"""

import os
from pathlib import Path

# Must be set before fixture import — session-scoped fixtures read these.
os.environ["FABRICIUM_TEST_PLUGIN_NAME"] = "fabricium-test-plugin"
os.environ["FABRICIUM_TEST_PLUGIN_DIR"] = str(Path(__file__).parent / "test_plugin")

from fabricium.testing.fixtures import hermes_config, hermes_test_env  # noqa: E402, F401

__all__ = ["hermes_config", "hermes_test_env"]
