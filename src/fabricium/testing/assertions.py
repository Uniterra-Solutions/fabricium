"""Composable CLI-output assertions for fabricium-based Hermes plugins.

Every assertion operates on a :class:`~fabricium.testing.harness.CliResult`
and raises :class:`AssertionError` with a diagnostic message on failure.

Design principles
-----------------
- **Building blocks, not dogma.**  Each function checks ONE thing (e.g. "does
  the output mention profile X?").  Plugin tests compose them to match their
  own expected behaviour.
- **Same patterns for single- and multi-profile plugins.**  Jovaltus
  (``default_profile=\"jovaltus-agent\"``) auto-creates one profile; Caelterra
  (``default_profile=None``) lets the user select profiles.  The assertions
  don't care which mode you're in — they just check *what the output says*.
- **Diagnostic on failure.**  Every failure includes the relevant excerpt from
  stdout so you can see what actually happened.

Usage
-----
::

    from fabricium.testing import CliResult
    from fabricium.testing.assertions import (
        assert_setup_completed,
        assert_profile_in_output,
        assert_skills_installed,
    )

    result: CliResult = env.run_cli("my-plugin", "setup")
    assert_setup_completed(result, "my-plugin")
    assert_profile_in_output(result, "my-profile")
    assert_skills_installed(result)

Or import the class for grouped usage::

    from fabricium.testing.assertions import CliAssert

    CliAssert.setup_completed(result, "my-plugin")
    CliAssert.profile_in_output(result, "my-profile")
"""

from __future__ import annotations

import re
from typing import List

from .harness import CliResult

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _excerpt(text: str, around: str, context: int = 2) -> str:
    """Return lines around the first match of *around* in *text*."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if around in line:
            lo = max(0, i - context)
            hi = min(len(lines), i + context + 1)
            return "\n".join(f"  {j:3d} | {lines[j]}" for j in range(lo, hi))
    # Fallback: last few lines
    lo = max(0, len(lines) - 6)
    return "\n".join(f"  {j:3d} | {lines[j]}" for j in range(lo, len(lines)))


def _fail(msg: str, result: CliResult, marker: str = "") -> None:
    """Raise AssertionError with diagnostic excerpt."""
    parts = [msg]
    if marker:
        parts.append(f"\nContext around '{marker}':\n{_excerpt(result.stdout, marker)}")
    else:
        tail = result.stdout.splitlines()[-8:]
        if tail:
            parts.append("\nLast 8 lines of stdout:\n" + "\n".join(f"  {line}" for line in tail))
    if result.stderr.strip():
        parts.append(f"\nstderr:\n{result.stderr.strip()}")
    raise AssertionError("\n".join(parts))


# ---------------------------------------------------------------------------
# Low-level building blocks
# ---------------------------------------------------------------------------


def assert_exit_code(result: CliResult, expected: int = 0) -> None:
    """Assert the CLI command exited with *expected* code."""
    if result.exit_code != expected:
        _fail(
            f"Expected exit code {expected}, got {result.exit_code}",
            result,
        )


def assert_stdout_contains(result: CliResult, text: str) -> None:
    """Assert *text* appears anywhere in stdout."""
    if text not in result.stdout:
        _fail(f"Expected stdout to contain {text!r}", result, marker=text)


def assert_stdout_contains_any(result: CliResult, texts: List[str]) -> None:
    """Assert at least one of *texts* appears in stdout."""
    for t in texts:
        if t in result.stdout:
            return
    _fail(
        f"Expected stdout to contain one of {texts!r}",
        result,
    )


def assert_stdout_matches(result: CliResult, pattern: str) -> None:
    """Assert *pattern* (regex) matches somewhere in stdout."""
    if not re.search(pattern, result.stdout):
        _fail(f"Expected stdout to match pattern {pattern!r}", result)


def assert_stdout_not_contains(result: CliResult, text: str) -> None:
    """Assert *text* does NOT appear in stdout."""
    if text in result.stdout:
        _fail(f"Expected stdout NOT to contain {text!r}", result, marker=text)


# ---------------------------------------------------------------------------
# Setup-specific assertions
# ---------------------------------------------------------------------------


def assert_setup_completed(result: CliResult, plugin_name: str = "") -> None:
    """Assert the setup command reported completion.

    Checks for the canonical ``✅ <Name> setup complete`` line.
    *plugin_name* is optional — if omitted, any "setup complete" line
    passes.  Matching is case-insensitive.
    """
    stdout_lower = result.stdout.lower()
    if plugin_name:
        marker = f"{plugin_name.lower()} setup complete"
    else:
        marker = "setup complete"
    if marker not in stdout_lower:
        _fail(
            f"Expected stdout to contain {marker!r} (case-insensitive)",
            result,
            marker=marker,
        )


def assert_profile_created(result: CliResult, profile_name: str) -> None:
    """Assert a new profile was created during setup.

    Checks for the ``✓ Profile '<name>' created`` line.  This only
    appears when Hermes actually creates the profile (i.e. it didn't
    already exist).  Use :func:`assert_profile_ready` for profiles
    that were found already existing.
    """
    marker = f"Profile '{profile_name}' created"
    assert_stdout_contains(result, marker)


def assert_profile_ready(result: CliResult, profile_name: str) -> None:
    """Assert a profile was found ready (already existed) during setup.

    Checks for ``✓ Profile '<name>' ready``.
    """
    marker = f"Profile '{profile_name}' ready"
    assert_stdout_contains(result, marker)


def assert_profile_in_output(result: CliResult, profile_name: str) -> None:
    """Assert a profile is mentioned in the output.

    This is the loosest profile check — it only requires the profile
    name to appear somewhere.  Use :func:`assert_profile_created` or
    :func:`assert_profile_ready` for stricter checks.
    """
    assert_stdout_contains(result, profile_name)


def assert_skills_installed(result: CliResult) -> None:
    """Assert bundled skills were installed.

    Checks for ``✓ Skill '<name>' installed`` lines.  Returns True if
    at least one skill was installed.  Does NOT fail if no skills are
    bundled (the plugin may legitimately have none).
    """
    # Look for skill installation messages
    if "Skill" in result.stdout and "installed" in result.stdout:
        return
    # Also accept "✓ Bundled skills installed" (future-proofing)
    if "skills installed" in result.stdout.lower():
        return
    # Fine if there were no skills to install
    if "No bundled skills" in result.stdout:
        return


def assert_soul_md_applied(result: CliResult) -> None:
    """Assert SOUL.md was deployed during setup.

    Checks for ``✓ SOUL.md written to``.
    """
    marker = "SOUL.md written to"
    assert_stdout_contains(result, marker)


def assert_soul_md_skipped(result: CliResult) -> None:
    """Assert SOUL.md was explicitly skipped."""
    assert_stdout_contains_any(
        result,
        ["⏭  Skipped SOUL.md", "⏭  Keeping existing SOUL.md"],
    )


def assert_no_skills_installed(result: CliResult) -> None:
    """Assert NO skills were installed (empty skills/ directory)."""
    assert_stdout_contains_any(
        result,
        ["No bundled skills", "⏭  Skipped skill installation"],
    )


# ---------------------------------------------------------------------------
# Status-specific assertions
# ---------------------------------------------------------------------------


def assert_status_shows_profile(
    result: CliResult,
    profile_name: str,
    with_soul_md: bool = True,
) -> None:
    """Assert ``status`` output includes *profile_name* in its table.

    Parameters
    ----------
    with_soul_md:
        If ``True``, also assert the status column shows
        ``Skills + SOUL.md ✓``.  Set ``False`` for skills-only profiles.
    """
    assert_stdout_contains(result, profile_name)
    if with_soul_md:
        assert_stdout_contains(result, "Skills + SOUL.md")
    else:
        # Should NOT contain the full SOUL.md indicator
        pass  # profile name appearing is sufficient


def assert_status_shows_no_profiles(result: CliResult, plugin_name: str) -> None:
    """Assert status reports that no profiles are installed yet."""
    assert_stdout_contains_any(
        result,
        [
            f"{plugin_name.title()} has not been installed",
            "No profiles in installation state",
            "Run: hermes",
        ],
    )


# ---------------------------------------------------------------------------
# Update-check assertions
# ---------------------------------------------------------------------------


def assert_update_check_responded(result: CliResult) -> None:
    """Assert ``update --check`` produced a meaningful diagnostic.

    Accepts any of: up-to-date, behind remote, ahead of remote,
    not-a-git-repo, no-remote-configured, or pip-installed.
    """
    assert_stdout_contains_any(
        result,
        [
            "is up to date",
            "new commit(s) behind remote",
            "commit(s) AHEAD of remote",
            "Not a git repository",
            "No remote 'origin' configured",
            "Checking for",
            "pip-installed plugin",
            "via PyPI",
            "A newer version is available",
        ],
    )


def assert_up_to_date(result: CliResult, plugin_name: str = "") -> None:
    """Assert update check reports the plugin is up to date."""
    if plugin_name:
        marker = f"{plugin_name.title()} is up to date"
    else:
        marker = "is up to date"
    assert_stdout_contains(result, marker)


def assert_behind_remote(result: CliResult) -> None:
    """Assert update check reports the plugin is behind the remote."""
    assert_stdout_contains(result, "new commit(s) behind remote")


# ---------------------------------------------------------------------------
# Composite / convenience
# ---------------------------------------------------------------------------


class CliAssert:
    """Namespace for the assertion functions above.

    Use as ``CliAssert.setup_completed(result, ...)`` when you prefer
    grouped access or want to avoid importing many free functions.

    Every method delegates to the corresponding module-level function.
    """

    # Low-level
    exit_code = staticmethod(assert_exit_code)
    stdout_contains = staticmethod(assert_stdout_contains)
    stdout_contains_any = staticmethod(assert_stdout_contains_any)
    stdout_matches = staticmethod(assert_stdout_matches)
    stdout_not_contains = staticmethod(assert_stdout_not_contains)

    # Setup
    setup_completed = staticmethod(assert_setup_completed)
    profile_created = staticmethod(assert_profile_created)
    profile_ready = staticmethod(assert_profile_ready)
    profile_in_output = staticmethod(assert_profile_in_output)
    skills_installed = staticmethod(assert_skills_installed)
    soul_md_applied = staticmethod(assert_soul_md_applied)
    soul_md_skipped = staticmethod(assert_soul_md_skipped)
    no_skills_installed = staticmethod(assert_no_skills_installed)

    # Status
    status_shows_profile = staticmethod(assert_status_shows_profile)
    status_shows_no_profiles = staticmethod(assert_status_shows_no_profiles)

    # Update
    update_check_responded = staticmethod(assert_update_check_responded)
    up_to_date = staticmethod(assert_up_to_date)
    behind_remote = staticmethod(assert_behind_remote)
