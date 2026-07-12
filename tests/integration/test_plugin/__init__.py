"""A minimal Hermes plugin that imports fabricium.

This plugin exists SOLELY for fabricium's own integration tests.
It registers via :class:`fabricium.HermesPlugin` and adds no extra tools.
"""

from pathlib import Path

from fabricium import HermesPlugin

plugin = HermesPlugin(
    name="fabricium-test-plugin",
    plugin_dir=Path(__file__).parent,
)


def register(ctx):  # noqa: D103  (Hermes convention)
    plugin.register(ctx)
