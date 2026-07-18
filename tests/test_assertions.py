"""Tests for fabricium.testing.assertions."""

import pytest

from fabricium.testing.assertions import (
    CliAssert,
    assert_behind_remote,
    assert_exit_code,
    assert_no_skills_installed,
    assert_profile_created,
    assert_profile_in_output,
    assert_profile_ready,
    assert_setup_completed,
    assert_skills_installed,
    assert_soul_md_applied,
    assert_soul_md_skipped,
    assert_status_shows_no_profiles,
    assert_status_shows_profile,
    assert_stdout_contains,
    assert_stdout_contains_any,
    assert_stdout_matches,
    assert_stdout_not_contains,
    assert_up_to_date,
    assert_update_check_responded,
)
from fabricium.testing.harness import CliResult


def _r(stdout="", stderr="", exit_code=0):
    return CliResult(exit_code=exit_code, stdout=stdout, stderr=stderr)


class TestLowLevel:
    def test_exit_code_passes(self):
        r = _r(exit_code=0)
        assert_exit_code(r, 0)

    def test_exit_code_fails_with_diagnostic(self):
        r = _r(exit_code=1, stdout="error output")
        with pytest.raises(AssertionError, match="Expected exit code 0"):
            assert_exit_code(r)

    def test_stdout_contains_passes(self):
        r = _r(stdout="hello world")
        assert_stdout_contains(r, "hello")

    def test_stdout_contains_fails_with_context(self):
        r = _r(stdout="line 1\nline 2\nline 3\nsearch target\nline 5")
        with pytest.raises(AssertionError, match="search target"):
            assert_stdout_contains(r, "not there")

    def test_stdout_contains_any_matches_first(self):
        r = _r(stdout="found beta")
        assert_stdout_contains_any(r, ["alpha", "beta", "gamma"])

    def test_stdout_contains_any_fails(self):
        r = _r(stdout="nothing relevant")
        with pytest.raises(AssertionError):
            assert_stdout_contains_any(r, ["alpha", "beta"])

    def test_stdout_matches_regex(self):
        r = _r(stdout="Profile 'my-profile' created")
        assert_stdout_matches(r, r"Profile '(.+)' created")

    def test_stdout_matches_fails(self):
        r = _r(stdout="no match here")
        with pytest.raises(AssertionError):
            assert_stdout_matches(r, r"Profile '(.+)' created")

    def test_stdout_not_contains_passes(self):
        r = _r(stdout="clean output")
        assert_stdout_not_contains(r, "error")

    def test_stdout_not_contains_fails(self):
        r = _r(stdout="error occurred")
        with pytest.raises(AssertionError, match="NOT to contain"):
            assert_stdout_not_contains(r, "error")

    def test_diagnostic_includes_stderr(self):
        r = _r(stdout="output", stderr="traceback details", exit_code=1)
        with pytest.raises(AssertionError, match="traceback details"):
            assert_exit_code(r)

    def test_diagnostic_excerpt_shows_context(self):
        r = _r(stdout="before\nProfile 'p' created\nafter")
        # This should pass fine — the excerpt logic is exercised in the
        # failure case above.  Here we just verify it formats cleanly.
        assert_stdout_contains(r, "Profile 'p' created")


class TestSetupAssertions:
    def test_setup_completed_with_name(self):
        r = _r(stdout="✅ Jovaltus setup complete.")
        assert_setup_completed(r, "jovaltus")

    def test_setup_completed_without_name(self):
        r = _r(stdout="✅ Caelterra setup complete.")
        assert_setup_completed(r)

    def test_setup_completed_case_insensitive_internal(self):
        # The function does case-insensitive via title()
        r = _r(stdout="✅ Jovaltus setup complete.")
        assert_setup_completed(r, "JOVALTUS")

    def test_profile_created(self):
        r = _r(stdout="✓ Profile 'jovaltus-agent' created")
        assert_profile_created(r, "jovaltus-agent")

    def test_profile_created_not_found(self):
        r = _r(stdout="Profile 'other' ready")
        with pytest.raises(AssertionError):
            assert_profile_created(r, "jovaltus-agent")

    def test_profile_ready(self):
        r = _r(stdout="✓ Profile 'default' ready")
        assert_profile_ready(r, "default")

    def test_profile_in_output_loose(self):
        r = _r(stdout="some text caelterra-profile more text")
        assert_profile_in_output(r, "caelterra-profile")

    def test_skills_installed_detects_install_line(self):
        r = _r(stdout="✓ Skill 'my-skill' installed to /path")
        assert_skills_installed(r)  # should not raise

    def test_skills_installed_no_skills_is_ok(self):
        r = _r(stdout="! No bundled skills directory found")
        assert_skills_installed(r)  # should not raise

    def test_no_skills_installed(self):
        r = _r(stdout="! No bundled skills directory found")
        assert_no_skills_installed(r)

    def test_soul_md_applied(self):
        r = _r(stdout="✓ SOUL.md written to /path/SOUL.md")
        assert_soul_md_applied(r)

    def test_soul_md_skipped(self):
        r = _r(stdout="⏭  Skipped SOUL.md")
        assert_soul_md_skipped(r)

    def test_soul_md_skipped_keeping_existing(self):
        r = _r(stdout="⏭  Keeping existing SOUL.md")
        assert_soul_md_skipped(r)


class TestStatusAssertions:
    def test_shows_profile_with_soul_md(self):
        r = _r(stdout="default              Skills + SOUL.md ✓      2026-01-01")
        assert_status_shows_profile(r, "default", with_soul_md=True)

    def test_shows_profile_without_soul_md(self):
        r = _r(stdout="my-profile           Skills only             2026-01-01")
        assert_status_shows_profile(r, "my-profile", with_soul_md=False)

    def test_no_profiles_message(self):
        r = _r(stdout="Jovaltus has not been installed to any profile yet.")
        assert_status_shows_no_profiles(r, "jovaltus")

    def test_no_profiles_alt_message(self):
        r = _r(stdout="No profiles in installation state.")
        assert_status_shows_no_profiles(r, "test")


class TestUpdateAssertions:
    def test_update_check_up_to_date(self):
        r = _r(stdout="✅ Jovaltus is up to date.")
        assert_update_check_responded(r)

    def test_update_check_behind(self):
        r = _r(stdout="📦 3 new commit(s) behind remote.")
        assert_update_check_responded(r)

    def test_update_check_not_git_repo(self):
        r = _r(stdout="! Not a git repository — cannot check for updates.")
        assert_update_check_responded(r)

    def test_update_check_no_remote(self):
        r = _r(stdout="! No remote 'origin' configured")
        assert_update_check_responded(r)

    def test_update_check_checking(self):
        r = _r(stdout="🔍 Checking for Test updates...")
        assert_update_check_responded(r)

    def test_update_check_pip_installed(self):
        msg = "🔍 pip-installed plugin — check for updates with:\n   pip install --upgrade test"
        r = _r(stdout=msg)
        assert_update_check_responded(r)

    def test_up_to_date_with_name(self):
        r = _r(stdout="✅ Jovaltus is up to date.")
        assert_up_to_date(r, "jovaltus")

    def test_behind_remote(self):
        r = _r(stdout="📦 5 new commit(s) behind remote.")
        assert_behind_remote(r)


class TestCliAssertClass:
    """Verify CliAssert delegates correctly."""

    def test_class_methods_work(self):
        r = _r(stdout="✅ Setup complete.")
        CliAssert.setup_completed(r)

    def test_class_low_level(self):
        r = _r(stdout="hello")
        CliAssert.stdout_contains(r, "hello")

    def test_class_exit_code(self):
        CliAssert.exit_code(_r(exit_code=0), 0)


class TestJovaltusScenario:
    """Simulate jovaltus single-profile setup."""

    JOVALTUS_SETUP_OUTPUT = """\
⚡ Jovaltus Setup
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📁 Profile
  Creating profile 'jovaltus-agent'...
  ✓ Profile 'jovaltus-agent' created

📚 Bundled Skills
  ✓ Skill 'jovaltus-agent' installed to /path/SKILL.md
    Load via: skill_view('jovaltus-agent')

🧠 Agent Identity (SOUL.md)
  ✓ SOUL.md written to /path/SOUL.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Jovaltus setup complete.
"""

    def test_jovaltus_setup_assertions(self):
        r = _r(stdout=self.JOVALTUS_SETUP_OUTPUT)
        assert_setup_completed(r, "jovaltus")
        assert_profile_created(r, "jovaltus-agent")
        assert_skills_installed(r)
        assert_soul_md_applied(r)
        assert_exit_code(r, 0)


class TestCaelterraScenario:
    """Simulate caelterra multi-profile setup."""

    CAELTERRA_SETUP_OUTPUT = """\
⚡ Caelterra Setup
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📁 Available profiles:
   1) default

  Selected profiles: default

📦 Installation mode:
  ✓ Mode: Skills + SOUL.md

────────────────────────────────────────
📁 Profile: default

  ✓ Skill 'caelterra-skill' installed to /path/SKILL.md

  ⏭  Keeping existing SOUL.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Caelterra setup complete for selected profiles.
"""

    def test_caelterra_setup_assertions(self):
        r = _r(stdout=self.CAELTERRA_SETUP_OUTPUT)
        assert_setup_completed(r, "caelterra")
        assert_profile_in_output(r, "default")
        assert_skills_installed(r)
        assert_soul_md_skipped(r)
        assert_exit_code(r, 0)

    def test_caelterra_no_profile_created(self):
        """Multi-profile mode does not create 'default' — it uses existing."""
        r = _r(stdout=self.CAELTERRA_SETUP_OUTPUT)
        with pytest.raises(AssertionError):
            assert_profile_created(r, "default")
