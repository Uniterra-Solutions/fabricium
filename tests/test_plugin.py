"""Tests for fabricium.HermesPlugin."""

from fabricium import HermesPlugin


def make_plugin(tmp_path, name="test-plugin"):
    """Helper to create a minimal HermesPlugin in a temp dir."""
    plugin_dir = tmp_path / name
    plugin_dir.mkdir()
    (plugin_dir / "SOUL.md").write_text("# Test Agent\n")
    skills_dir = plugin_dir / "skills"
    skills_dir.mkdir()
    for skill_name in ("skill-x",):
        sd = skills_dir / skill_name
        sd.mkdir()
        (sd / "SKILL.md").write_text(f"---\nname: {skill_name}\n---\n# {skill_name}\n")
    return HermesPlugin(name=name, plugin_dir=plugin_dir)


class TestHermesPluginInit:
    def test_basic_attributes(self, tmp_path):
        plugin = make_plugin(tmp_path, "foo")
        assert plugin.name == "foo"
        assert plugin.default_profile is None

    def test_with_default_profile(self, tmp_path):
        plugin_dir = tmp_path / "bar"
        plugin_dir.mkdir()
        plugin = HermesPlugin(name="bar", plugin_dir=plugin_dir, default_profile="bar-profile")
        assert plugin.default_profile == "bar-profile"

    def test_custom_soul_md_path(self, tmp_path):
        plugin_dir = tmp_path / "baz"
        plugin_dir.mkdir()
        (plugin_dir / "CUSTOM.md").write_text("# Custom\n")
        plugin = HermesPlugin(name="baz", plugin_dir=plugin_dir, soul_md_path="CUSTOM.md")
        assert plugin.soul_md_path == "CUSTOM.md"


class TestHermesPluginStateIntegration:
    def test_set_and_load_state(self, tmp_hermes_home, tmp_path):
        import os

        os.environ["HERMES_HOME"] = str(tmp_hermes_home)
        plugin = make_plugin(tmp_path, "test-plugin")
        plugin._set_profile_state("p1", True)
        s = plugin._load_state()
        assert "p1" in s["profiles"]
        assert s["profiles"]["p1"]["soul_md"] is True


class TestApplySoulMd:
    def test_writes_soul_md_to_profile(self, tmp_hermes_home, tmp_path):
        import os

        os.environ["HERMES_HOME"] = str(tmp_hermes_home)
        # Set up a profile dir
        profiles_dir = tmp_hermes_home / "profiles" / "test-profile"
        profiles_dir.mkdir(parents=True)
        (profiles_dir / "config.yaml").write_text("provider: test\n")

        plugin = make_plugin(tmp_path, "test-plugin")
        result = plugin._apply_soul_md("test-profile")
        assert result is True
        assert (profiles_dir / "SOUL.md").exists()
        assert (profiles_dir / "SOUL.md").read_text() == "# Test Agent\n"

    def test_returns_false_when_soul_md_missing(self, tmp_hermes_home, tmp_path):
        import os

        os.environ["HERMES_HOME"] = str(tmp_hermes_home)
        plugin_dir = tmp_path / "nosoul"
        plugin_dir.mkdir()
        (plugin_dir / "skills").mkdir()
        plugin = HermesPlugin(name="nosoul", plugin_dir=plugin_dir)
        result = plugin._apply_soul_md("test-profile")
        assert result is False


class TestListProfiles:
    def test_no_profiles_when_empty(self, tmp_hermes_home, tmp_path):
        import os

        os.environ["HERMES_HOME"] = str(tmp_hermes_home)
        plugin = make_plugin(tmp_path, "test-plugin")
        profiles = plugin._list_profiles()
        assert profiles == []

    def test_detects_default_profile(self, tmp_hermes_home, tmp_path):
        import os

        os.environ["HERMES_HOME"] = str(tmp_hermes_home)
        (tmp_hermes_home / "config.yaml").write_text("provider: test\n")
        plugin = make_plugin(tmp_path, "test-plugin")
        profiles = plugin._list_profiles()
        assert "default" in profiles

    def test_detects_named_profiles(self, tmp_hermes_home, tmp_path):
        import os

        os.environ["HERMES_HOME"] = str(tmp_hermes_home)
        pdir = tmp_hermes_home / "profiles" / "my-profile"
        pdir.mkdir(parents=True)
        (pdir / "config.yaml").write_text("provider: test\n")
        plugin = make_plugin(tmp_path, "test-plugin")
        profiles = plugin._list_profiles()
        assert "my-profile" in profiles


class TestEnsureProfile:
    def test_returns_true_when_profile_exists(self, tmp_hermes_home, tmp_path):
        import os

        os.environ["HERMES_HOME"] = str(tmp_hermes_home)
        pdir = tmp_hermes_home / "profiles" / "exists"
        pdir.mkdir(parents=True)
        (pdir / "config.yaml").write_text("provider: test\n")
        plugin = make_plugin(tmp_path, "test-plugin")
        assert plugin._ensure_profile("exists") is True

    def test_returns_false_when_hermes_cli_missing(self, tmp_hermes_home, tmp_path, monkeypatch):
        """When hermes CLI is not found, ensure_profile should return False."""
        import os
        import subprocess

        os.environ["HERMES_HOME"] = str(tmp_hermes_home)

        # Simulate hermes CLI being unavailable
        original_run = subprocess.run

        def fake_run(cmd, **kwargs):
            if cmd[0] == "hermes":
                raise FileNotFoundError("hermes CLI not found")
            return original_run(cmd, **kwargs)

        monkeypatch.setattr(subprocess, "run", fake_run)

        plugin = make_plugin(tmp_path, "test-plugin")
        result = plugin._ensure_profile("nonexistent")
        assert result is False


# ── Regression tests ─────────────────────────────────────────────


class TestEncodingRegression:
    """Bug 1: Windows cp950 — encoding="utf-8" prevents UnicodeDecodeError."""

    def test_utf8_roundtrip_via_state_save_load(self, tmp_hermes_home):
        """Em dash, curly quotes, Chinese survive state save → load."""
        import os

        from fabricium import state as state_mod

        os.environ["HERMES_HOME"] = str(tmp_hermes_home)
        # Clear cache so we pick up the new HERMES_HOME
        state_mod._HERMES_HOME_CACHE = None
        name = "enc-test"
        state_mod.save_state(
            name,
            {"profiles": {"p1": {"note": "em dash — curly \u201cquote\u201d 中文"}}},
        )
        loaded = state_mod.load_state(name)
        assert loaded["profiles"]["p1"]["note"] == "em dash — curly \u201cquote\u201d 中文"

    def test_utf8_soul_md_roundtrip(self, tmp_hermes_home, tmp_path):
        """SOUL.md with non-ASCII chars is copied faithfully."""
        import os

        os.environ["HERMES_HOME"] = str(tmp_hermes_home)
        plugin_dir = tmp_path / "enc-plugin"
        plugin_dir.mkdir()
        soul_content = "# Agent \u2014 non-ASCII test: caf\u00e9 \u4e2d\u6587\n"
        (plugin_dir / "SOUL.md").write_text(soul_content, encoding="utf-8")

        plugin = HermesPlugin(name="enc-plugin", plugin_dir=plugin_dir)
        profile_dir = tmp_hermes_home / "profiles" / "p1"
        profile_dir.mkdir(parents=True)

        plugin._apply_soul_md("p1")
        written = (profile_dir / "SOUL.md").read_text(encoding="utf-8")
        assert written == soul_content


class TestResolveUpdateMode:
    """Bug 3: _resolve_update_mode defaults to pip, not git."""

    def test_defaults_to_pip(self, tmp_path):
        """When neither --git nor --pip is given, use_pip=True."""
        from types import SimpleNamespace

        plugin = make_plugin(tmp_path, "test-plugin")
        args = SimpleNamespace(git=False, pip=False)
        use_git, use_pip = plugin._resolve_update_mode(args)
        assert use_pip is True
        assert use_git is False

    def test_git_flag_overrides(self, tmp_path):
        """--git flag forces git mode."""
        from types import SimpleNamespace

        plugin = make_plugin(tmp_path, "test-plugin")
        args = SimpleNamespace(git=True, pip=False)
        use_git, use_pip = plugin._resolve_update_mode(args)
        assert use_git is True
        assert use_pip is False

    def test_pip_flag_overrides(self, tmp_path):
        """--pip flag forces pip mode."""
        from types import SimpleNamespace

        plugin = make_plugin(tmp_path, "test-plugin")
        args = SimpleNamespace(git=False, pip=True)
        use_git, use_pip = plugin._resolve_update_mode(args)
        assert use_pip is True
        assert use_git is False


class TestUpdateCheckPip:
    """Bug 3: _update_check_pip returns bool for caller fallback logic."""

    def test_returns_true_when_up_to_date(self, tmp_path, monkeypatch):
        """pip reports 'Requirement already satisfied' → True."""
        import subprocess

        plugin = make_plugin(tmp_path, "test-plugin")

        def fake_run(cmd, **kwargs):
            return subprocess.CompletedProcess(
                cmd, 0, stdout="Requirement already satisfied\n", stderr=""
            )

        monkeypatch.setattr(subprocess, "run", fake_run)
        result = plugin._update_check_pip()
        assert result is True

    def test_returns_false_when_pip_not_found(self, tmp_path, monkeypatch):
        """pip binary missing → False."""
        import subprocess

        plugin = make_plugin(tmp_path, "test-plugin")

        def fake_run(cmd, **kwargs):
            raise FileNotFoundError("pip not found")

        monkeypatch.setattr(subprocess, "run", fake_run)
        result = plugin._update_check_pip()
        assert result is False

    def test_returns_false_when_check_fails(self, tmp_path, monkeypatch):
        """pip exits non-zero (e.g. package not on PyPI) → False."""
        import subprocess

        plugin = make_plugin(tmp_path, "test-plugin")

        def fake_run(cmd, **kwargs):
            return subprocess.CompletedProcess(
                cmd, 1, stdout="", stderr="ERROR: No matching distribution found\n"
            )

        monkeypatch.setattr(subprocess, "run", fake_run)
        result = plugin._update_check_pip()
        assert result is False

    def test_returns_true_when_would_install(self, tmp_path, monkeypatch):
        """pip reports 'Would install' → True (newer version available)."""
        import subprocess

        plugin = make_plugin(tmp_path, "test-plugin")

        def fake_run(cmd, **kwargs):
            return subprocess.CompletedProcess(
                cmd,
                0,
                stdout="Would install test-plugin-2.0.0\n",
                stderr="",
            )

        monkeypatch.setattr(subprocess, "run", fake_run)
        result = plugin._update_check_pip()
        assert result is True


class TestUpdateCheckPipExitCodeOrdering:
    """REVIEW BUG: text-pattern matching takes priority over exit-code check.

    If pip exits non-zero but stderr happens to contain a matched pattern
    (e.g. from a dependency), _update_check_pip incorrectly returns True.
    """

    def test_nonzero_exit_with_matching_text_returns_false(self, tmp_path, monkeypatch):
        """pip exits non-zero with matched text in stderr → False not True."""
        import subprocess

        plugin = make_plugin(tmp_path, "test-plugin")

        def fake_run(cmd, **kwargs):
            # Simulate pip failing with error that mentions a satisfied dependency
            return subprocess.CompletedProcess(
                cmd,
                1,
                stdout="",
                stderr=(
                    "ERROR: Could not find a version that satisfies the "
                    "requirement test-plugin\n"
                    "Requirement already satisfied: some-dep in /usr/lib\n"
                ),
            )

        monkeypatch.setattr(subprocess, "run", fake_run)
        result = plugin._update_check_pip()
        assert result is False, (
            "Should return False when exit code is non-zero, even if output matches a pattern"
        )

    def test_nonzero_exit_with_would_install_text_returns_false(self, tmp_path, monkeypatch):
        """pip exits non-zero with 'Would install' in stderr → False not True."""
        import subprocess

        plugin = make_plugin(tmp_path, "test-plugin")

        def fake_run(cmd, **kwargs):
            return subprocess.CompletedProcess(
                cmd,
                1,
                stdout="",
                stderr=("ERROR: pip failed\nWould install test-plugin-2.0.0\n"),
            )

        monkeypatch.setattr(subprocess, "run", fake_run)
        result = plugin._update_check_pip()
        assert result is False, (
            "Should return False when exit code is non-zero, "
            "even if output contains 'Would install'"
        )


class TestUpdatePullPip:
    """Bug 3: _update_pull_pip returns True when pip functional, False only when pip missing."""

    def test_returns_true_when_already_satisfied(self, tmp_path, monkeypatch):
        """'Requirement already satisfied' → True (pip is functional)."""
        import subprocess

        plugin = make_plugin(tmp_path, "test-plugin")

        call_count = 0

        def fake_run(cmd, **kwargs):
            nonlocal call_count
            call_count += 1
            if "--version" in cmd:
                return subprocess.CompletedProcess(cmd, 0, stdout="pip 24.0\n", stderr="")
            return subprocess.CompletedProcess(
                cmd, 0, stdout="Requirement already satisfied\n", stderr=""
            )

        monkeypatch.setattr(subprocess, "run", fake_run)
        result = plugin._update_pull_pip()
        assert result is True  # pip was functional

    def test_returns_false_when_pip_not_found(self, tmp_path, monkeypatch):
        """pip --version fails → False (trigger git fallback)."""
        import subprocess

        plugin = make_plugin(tmp_path, "test-plugin")

        def fake_run(cmd, **kwargs):
            raise FileNotFoundError("pip not found")

        monkeypatch.setattr(subprocess, "run", fake_run)
        result = plugin._update_pull_pip()
        assert result is False  # triggers git fallback

    def test_returns_true_when_fresh_install_succeeds(self, tmp_path, monkeypatch):
        """pip install succeeds with 'Successfully installed' → True."""
        import subprocess

        plugin = make_plugin(tmp_path, "test-plugin")

        def fake_run(cmd, **kwargs):
            if "--version" in cmd:
                return subprocess.CompletedProcess(cmd, 0, stdout="pip 24.0\n", stderr="")
            return subprocess.CompletedProcess(
                cmd,
                0,
                stdout="Successfully installed test-plugin-2.0.0\n",
                stderr="",
            )

        monkeypatch.setattr(subprocess, "run", fake_run)
        result = plugin._update_pull_pip()
        assert result is True  # pip was functional, update succeeded
