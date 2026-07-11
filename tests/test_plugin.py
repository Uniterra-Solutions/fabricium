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
