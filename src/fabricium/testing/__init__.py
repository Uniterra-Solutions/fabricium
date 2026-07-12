"""Fabricium integration-test infrastructure.

Import :class:`~fabricium.testing.harness.HermesDockerTestEnv` directly for
programmatic use, or use the :mod:`~fabricium.testing.fixtures` module for
pytest-based testing.  The :mod:`~fabricium.testing.assertions` module
provides composable CLI-output assertions for verifying plugin behaviour.
"""

from fabricium.testing.assertions import CliAssert
from fabricium.testing.harness import (
    CliResult,
    HermesConfig,
    HermesDockerTestEnv,
)

__all__ = [
    "CliAssert",
    "CliResult",
    "HermesConfig",
    "HermesDockerTestEnv",
]
