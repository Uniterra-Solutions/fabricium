"""Reusable pytest fixtures for Hermes plugin integration testing.

Provides session-scoped Docker management and function-scoped test
environments.  Plugin authors (caelterra, jovaltus, …) can import these
fixtures in their own ``conftest.py``::

    # my_plugin/tests/conftest.py
    import os
    from pathlib import Path

    # Set before importing the fixture — it reads these at call time.
    os.environ["FABRICIUM_TEST_PLUGIN_NAME"] = "my-plugin"
    os.environ["FABRICIUM_TEST_PLUGIN_DIR"] = str(Path(__file__).parent.parent)

    from fabricium.testing.fixtures import hermes_test_env
    __all__ = ["hermes_test_env"]

Fixtures
--------
``hermes_config`` (session)
    Hermes provider / model configuration from environment.
``hermes_test_env`` (session)
    Yields a :class:`~fabricium.testing.harness.HermesDockerTestEnv`.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

import pytest

from .harness import HermesConfig, HermesDockerTestEnv


def _discover_fabricium_src() -> Path | None:
    """Walk up from this file to find the fabricium source root."""
    here = Path(__file__).resolve().parent
    for parent in [here] + list(here.parents):
        if (parent / "pyproject.toml").exists():
            return parent
    return None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def hermes_config() -> HermesConfig:
    """Session-scoped Hermes configuration from environment.

    Reads from: ``FABRICIUM_TEST_PROVIDER``, ``FABRICIUM_TEST_MODEL``,
    ``FABRICIUM_TEST_API_KEY`` (or provider-specific ``<PROVIDER>_API_KEY``).
    """
    return HermesConfig()


def _get_plugin_name() -> str:
    """Resolve plugin name from env var."""
    name = os.environ.get("FABRICIUM_TEST_PLUGIN_NAME", "")
    if not name:
        raise pytest.UsageError(
            "Set FABRICIUM_TEST_PLUGIN_NAME env var to the plugin's CLI name.\n"
            "Example: export FABRICIUM_TEST_PLUGIN_NAME=caelterra"
        )
    return name


def _get_plugin_dir() -> Path:
    """Resolve plugin directory from env var."""
    raw = os.environ.get("FABRICIUM_TEST_PLUGIN_DIR", "")
    if not raw:
        raise pytest.UsageError(
            "Set FABRICIUM_TEST_PLUGIN_DIR env var to the plugin's source directory.\n"
            "Example: export FABRICIUM_TEST_PLUGIN_DIR=/path/to/my-plugin"
        )
    return Path(raw).resolve()


@pytest.fixture(scope="session")
def hermes_test_env(
    hermes_config: HermesConfig,
) -> Generator[HermesDockerTestEnv, None, None]:
    """Session-scoped Docker-based Hermes test environment.

    Requires ``FABRICIUM_TEST_PLUGIN_NAME`` and ``FABRICIUM_TEST_PLUGIN_DIR``
    environment variables to be set before test collection.

    Optional env vars
    -----------------
    ``FABRICIUM_TEST_FABRICIUM_SRC``
        Override the auto-discovered fabricium source path.  Set to empty
        string to skip fabricium installation entirely (e.g. for plugins
        that vendor fabricium or don't depend on it).
    ``FABRICIUM_TEST_SKIP_FABRICIUM_INSTALL``
        Set to ``\"1\"`` to skip ``uv pip install fabricium`` inside the
        container.  Use when the plugin vendors fabricium (caelterra) or
        doesn't need it at runtime (jovaltus).
    ``FABRICIUM_TEST_KEEP``
        Set to ``\"1\"`` to keep the container after test failure.
    """
    plugin_name = _get_plugin_name()
    plugin_dir = _get_plugin_dir()

    # Fabricium source — env override or auto-discover
    raw_src = os.environ.get("FABRICIUM_TEST_FABRICIUM_SRC", "")
    if raw_src == "":
        fabricium_src = None
    elif raw_src:
        fabricium_src = Path(raw_src).resolve()
    else:
        fabricium_src = _discover_fabricium_src()

    keep = os.environ.get("FABRICIUM_TEST_KEEP", "") == "1"
    skip_install = os.environ.get("FABRICIUM_TEST_SKIP_FABRICIUM_INSTALL", "") == "1"

    env = HermesDockerTestEnv(
        plugin_name=plugin_name,
        plugin_dir=plugin_dir,
        fabricium_src=fabricium_src,
        config=hermes_config,
        keep=keep,
    )
    try:
        env.start(skip_fabricium_install=skip_install)
        yield env
    finally:
        env.stop()
