"""Integration tests: verify fabricium-based plugins work in real Hermes."""

from fabricium.testing.assertions import (
    assert_exit_code,
    assert_no_skills_installed,
    assert_profile_in_output,
    assert_setup_completed,
    assert_soul_md_skipped,
    assert_update_check_responded,
)
from fabricium.testing.harness import HermesDockerTestEnv

PLUGIN = "fabricium-test-plugin"


def test_hermes_is_available(hermes_test_env: HermesDockerTestEnv) -> None:
    """Sanity check: the container has a working Hermes CLI."""
    result = hermes_test_env.run_cli("--version")
    assert_exit_code(result)


class TestPluginCli:
    """Verify that a fabricium-based plugin's CLI commands work."""

    def test_setup_runs_and_completes(self, hermes_test_env: HermesDockerTestEnv) -> None:
        """``hermes <plugin> setup`` should complete successfully."""
        result = hermes_test_env.run_cli(PLUGIN, "setup", timeout=90)

        assert_exit_code(result)
        assert_setup_completed(result, PLUGIN)
        # The test plugin has NO skills/ dir → expect no skills installed
        assert_no_skills_installed(result)
        # Non-TTY mode defaults to keeping existing SOUL.md
        assert_soul_md_skipped(result)

    def test_status_shows_profile_after_setup(self, hermes_test_env: HermesDockerTestEnv) -> None:
        """After setup, ``hermes <plugin> status`` mentions the profile."""
        hermes_test_env.run_cli(PLUGIN, "setup", timeout=90)

        result = hermes_test_env.run_cli(PLUGIN, "status")
        assert_exit_code(result)
        assert_profile_in_output(result, "default")

    def test_update_check_works(self, hermes_test_env: HermesDockerTestEnv) -> None:
        """``hermes <plugin> update --check`` should produce a diagnostic."""
        result = hermes_test_env.run_cli(PLUGIN, "update", "--check", timeout=90)
        assert_update_check_responded(result)


class TestCliGracefulErrors:
    """Verify CLI handles edge cases gracefully."""

    def test_unknown_subcommand(self, hermes_test_env: HermesDockerTestEnv) -> None:
        """Unknown subcommand should fail with non-zero exit."""
        result = hermes_test_env.run_cli(PLUGIN, "nonexistent-command")
        assert result.exit_code != 0

    def test_setup_is_idempotent(self, hermes_test_env: HermesDockerTestEnv) -> None:
        """Running setup twice should succeed both times."""
        r1 = hermes_test_env.run_cli(PLUGIN, "setup", timeout=90)
        assert_exit_code(r1)

        r2 = hermes_test_env.run_cli(PLUGIN, "setup", timeout=90)
        assert_exit_code(r2)


class TestSelfBootstrap:
    """Verify plugins self-bootstrap their fabricium dependency.

    When Hermes recreates its venv (e.g. during an update), plugin-only
    dependencies like fabricium are lost.  The _ensure_fabricium() guard
    in the plugin's __init__.py must detect the missing import and
    ``pip install`` fabricium before the plugin registers its CLI.
    """

    def test_plugin_self_bootstraps_missing_fabricium(self) -> None:
        """Plugin CLI works even when fabricium is NOT pre-installed."""
        import shutil
        import tempfile
        from pathlib import Path

        from fabricium.testing.harness import HermesConfig, HermesDockerTestEnv

        plugin_dir = Path(__file__).parent / "test_plugin"
        fabricium_src = Path(__file__).parent.parent.parent

        config = HermesConfig()
        env = HermesDockerTestEnv(
            plugin_name=PLUGIN,
            plugin_dir=plugin_dir,
            fabricium_src=fabricium_src,
            config=config,
        )
        try:
            # Start WITHOUT pre-installing fabricium — the plugin must self-bootstrap
            env.start(skip_fabricium_install=True)

            # Verify the CLI command is registered (proves fabricium was bootstrapped)
            result = env.run_cli(PLUGIN, "status")
            assert_exit_code(result)
            assert result.contains("No profiles in installation state")

        finally:
            env.stop()
