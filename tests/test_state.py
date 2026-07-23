"""Tests for fabricium.state."""

import os
from pathlib import Path

from fabricium import state


def test_get_global_hermes_home_from_env():
    """When HERMES_HOME points to a profile dir, we resolve to the global home."""
    old = os.environ.get("HERMES_HOME")
    try:
        os.environ["HERMES_HOME"] = "/Users/test/.hermes/profiles/my-profile"
        result = state._get_global_hermes_home()
        assert str(result) == "/Users/test/.hermes"
    finally:
        if old is not None:
            os.environ["HERMES_HOME"] = old
        else:
            os.environ.pop("HERMES_HOME", None)


def test_get_global_hermes_home_when_not_under_profiles():
    """When HERMES_HOME does not contain 'profiles', return it as-is."""
    old = os.environ.get("HERMES_HOME")
    try:
        os.environ["HERMES_HOME"] = "/custom/hermes"
        result = state._get_global_hermes_home()
        assert str(result) == "/custom/hermes"
    finally:
        if old is not None:
            os.environ["HERMES_HOME"] = old
        else:
            os.environ.pop("HERMES_HOME", None)


def test_get_global_hermes_home_default(tmp_hermes_home, monkeypatch):
    """Without HERMES_HOME and without hermes CLI, falls back to ~/.hermes."""
    import subprocess

    import fabricium.state as state_mod

    old = os.environ.get("HERMES_HOME")
    old_cache = state_mod._HERMES_HOME_CACHE
    try:
        os.environ.pop("HERMES_HOME", None)
        state_mod._HERMES_HOME_CACHE = None

        # Simulate hermes CLI being unavailable
        original_run = subprocess.run

        def fake_run(cmd, **kwargs):
            if isinstance(cmd, list) and cmd[0] == "hermes":
                raise FileNotFoundError("hermes not found")
            return original_run(cmd, **kwargs)

        import fabricium.state

        monkeypatch.setattr(fabricium.state.subprocess, "run", fake_run)

        result = state._get_global_hermes_home()
        assert result.name == ".hermes"
    finally:
        if old is not None:
            os.environ["HERMES_HOME"] = old
        state_mod._HERMES_HOME_CACHE = old_cache


def test_get_state_path():
    path = state.get_state_path("my-plugin")
    assert path.name == "my-plugin_state.json"
    assert ".hermes" in str(path)


def test_load_state_empty(tmp_hermes_home):
    """Loading state when no file exists returns empty dict."""
    os.environ["HERMES_HOME"] = str(tmp_hermes_home)
    result = state.load_state("test-plugin")
    assert result == {"profiles": {}}


def test_save_and_load_state(tmp_hermes_home):
    """Save then load preserves data."""
    os.environ["HERMES_HOME"] = str(tmp_hermes_home)
    data = {"profiles": {"my-profile": {"soul_md": True, "updated_at": "2026-01-01"}}}
    state.save_state("test-plugin", data)
    loaded = state.load_state("test-plugin")
    assert loaded == data


def test_set_profile_state(tmp_hermes_home):
    """set_profile_state records a profile."""
    os.environ["HERMES_HOME"] = str(tmp_hermes_home)
    state.set_profile_state("test-plugin", "my-profile", True)
    loaded = state.load_state("test-plugin")
    assert "my-profile" in loaded["profiles"]
    assert loaded["profiles"]["my-profile"]["soul_md"] is True
    assert "updated_at" in loaded["profiles"]["my-profile"]


def test_set_profile_state_without_soul_md(tmp_hermes_home):
    """set_profile_state with soul_md=False."""
    os.environ["HERMES_HOME"] = str(tmp_hermes_home)
    state.set_profile_state("test-plugin", "my-profile", False)
    loaded = state.load_state("test-plugin")
    assert loaded["profiles"]["my-profile"]["soul_md"] is False


def test_load_state_corrupted_json(tmp_hermes_home):
    """Corrupted JSON returns empty dict."""
    os.environ["HERMES_HOME"] = str(tmp_hermes_home)
    state_path = state.get_state_path("test-plugin")
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text("not valid json {{{")
    result = state.load_state("test-plugin")
    assert result == {"profiles": {}}


def test_load_state_non_dict_json(tmp_hermes_home):
    """Non-dict JSON returns empty dict."""
    os.environ["HERMES_HOME"] = str(tmp_hermes_home)
    state_path = state.get_state_path("test-plugin")
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text("[1, 2, 3]")
    result = state.load_state("test-plugin")
    assert result == {"profiles": {}}


def test_multiple_profiles_state(tmp_hermes_home):
    """Multiple profiles can coexist in state."""
    os.environ["HERMES_HOME"] = str(tmp_hermes_home)
    state.set_profile_state("test-plugin", "profile-a", True)
    state.set_profile_state("test-plugin", "profile-b", False)
    loaded = state.load_state("test-plugin")
    assert len(loaded["profiles"]) == 2
    assert loaded["profiles"]["profile-a"]["soul_md"] is True
    assert loaded["profiles"]["profile-b"]["soul_md"] is False


# ── Path resolution tests ──────────────────────────────────────────


class TestDeriveGlobalHomeFromConfigPath:
    def test_under_profiles_goes_up_two_levels(self):
        config = Path("/Users/test/.hermes/profiles/my-profile/config.yaml")
        home = state._derive_global_home_from_config_path(config)
        assert str(home) == "/Users/test/.hermes"

    def test_not_under_profiles_returns_parent(self):
        config = Path("/Users/test/.hermes/config.yaml")
        home = state._derive_global_home_from_config_path(config)
        assert str(home) == "/Users/test/.hermes"

    def test_custom_path_not_under_profiles(self):
        config = Path("/opt/hermes/config.yaml")
        home = state._derive_global_home_from_config_path(config)
        assert str(home) == "/opt/hermes"


class TestResolveHermesHomeViaCli:
    def test_returns_none_when_cli_not_found(self, monkeypatch):
        import subprocess

        def fake_run(cmd, **kwargs):
            if isinstance(cmd, list) and cmd[0] == "hermes":
                raise FileNotFoundError("hermes not found")
            return subprocess.run(cmd, **kwargs)

        monkeypatch.setattr(state.subprocess, "run", fake_run)
        result = state._resolve_hermes_home_via_cli()
        assert result is None

    def test_returns_none_when_cli_fails(self, monkeypatch):
        import subprocess

        def fake_run(cmd, **kwargs):
            if isinstance(cmd, list) and cmd[0] == "hermes":
                raise subprocess.CalledProcessError(1, cmd)
            return subprocess.run(cmd, **kwargs)

        monkeypatch.setattr(state.subprocess, "run", fake_run)
        result = state._resolve_hermes_home_via_cli()
        assert result is None

    def test_returns_none_when_cli_timeout(self, monkeypatch):
        import subprocess

        def fake_run(cmd, **kwargs):
            if isinstance(cmd, list) and cmd[0] == "hermes":
                raise subprocess.TimeoutExpired(cmd, 5)
            return subprocess.run(cmd, **kwargs)

        monkeypatch.setattr(state.subprocess, "run", fake_run)
        result = state._resolve_hermes_home_via_cli()
        assert result is None

    def test_returns_home_when_cli_succeeds(self, monkeypatch):
        """When hermes config path returns a profile path, derive global home."""
        from subprocess import CompletedProcess

        import fabricium.state as state_mod

        old_cache = state_mod._HERMES_HOME_CACHE
        try:
            state_mod._HERMES_HOME_CACHE = None

            def fake_run(cmd, capture_output=False, text=False, timeout=None, **_):
                if isinstance(cmd, list) and cmd == ["hermes", "config", "path"]:
                    return CompletedProcess(
                        cmd,
                        0,
                        stdout="/tmp/.hermes/profiles/test-profile/config.yaml\n",
                        stderr="",
                    )
                raise AssertionError(f"Unexpected subprocess call: {cmd}")

            monkeypatch.setattr(state.subprocess, "run", fake_run)
            result = state._resolve_hermes_home_via_cli()
            assert result is not None
            assert str(result).endswith("/.hermes")
        finally:
            state_mod._HERMES_HOME_CACHE = old_cache


class TestGetGlobalHermesHomeCache:
    def test_cli_resolution_is_cached(self, monkeypatch, tmp_hermes_home):
        """The CLI is only called once; subsequent calls use the cache."""
        import os
        import subprocess

        import fabricium.state as state_mod

        old_env = os.environ.get("HERMES_HOME")
        old_cache = state_mod._HERMES_HOME_CACHE
        call_count = 0
        try:
            os.environ.pop("HERMES_HOME", None)
            state_mod._HERMES_HOME_CACHE = None

            original_run = subprocess.run

            def fake_run(cmd, **kwargs):
                nonlocal call_count
                if isinstance(cmd, list) and cmd[0] == "hermes":
                    call_count += 1
                    raise FileNotFoundError("hermes not found")
                return original_run(cmd, **kwargs)

            monkeypatch.setattr(state.subprocess, "run", fake_run)

            # First call — triggers CLI resolution, caches result
            r1 = state._get_global_hermes_home()
            assert call_count == 1
            # Second call — uses cache
            r2 = state._get_global_hermes_home()
            assert call_count == 1  # still 1, no second subprocess call
            assert r1 == r2
        finally:
            if old_env is not None:
                os.environ["HERMES_HOME"] = old_env
            state_mod._HERMES_HOME_CACHE = old_cache


class TestGetHermesPython:
    def test_returns_venv_python_when_exists(self, tmp_hermes_home):
        """When .venv/bin/python3 exists, return that path."""
        venv_python = tmp_hermes_home / ".venv" / "bin" / "python3"
        venv_python.parent.mkdir(parents=True)
        venv_python.touch()

        result = state._get_hermes_python()
        assert str(Path(result).resolve()) == str(venv_python.resolve())

    def test_falls_back_to_sys_executable_when_venv_missing(self, tmp_hermes_home):
        """When .venv/ doesn't exist, fall back to sys.executable."""
        import sys

        result = state._get_hermes_python()
        assert result == sys.executable

    def test_windows_uses_scripts_python_exe(self, tmp_hermes_home, monkeypatch):
        """On Windows, use .venv/Scripts/python.exe."""
        monkeypatch.setattr(state.sys, "platform", "win32")
        venv_python = tmp_hermes_home / ".venv" / "Scripts" / "python.exe"
        venv_python.parent.mkdir(parents=True)
        venv_python.touch()

        result = state._get_hermes_python()
        assert str(Path(result).resolve()) == str(venv_python.resolve())

    def test_falls_back_to_sys_when_venv_bin_empty(self, tmp_hermes_home):
        """When .venv/bin exists but contains no python/python3, fall back."""
        import sys

        bin_dir = tmp_hermes_home / ".venv" / "bin"
        bin_dir.mkdir(parents=True)

        result = state._get_hermes_python()
        assert result == sys.executable

    def test_returns_venv_python_when_only_python_exists(self, tmp_hermes_home):
        """When .venv/bin/python exists but python3 does NOT, use python."""
        bin_dir = tmp_hermes_home / ".venv" / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "python").touch()

        result = state._get_hermes_python()
        expected = (tmp_hermes_home / ".venv" / "bin" / "python").resolve()
        assert str(Path(result).resolve()) == str(expected)

    def test_windows_falls_back_to_python_when_python_exe_missing(
        self, tmp_hermes_home, monkeypatch
    ):
        """On Windows, when python.exe missing but python exists, use python."""
        monkeypatch.setattr(state.sys, "platform", "win32")
        bin_dir = tmp_hermes_home / ".venv" / "Scripts"
        bin_dir.mkdir(parents=True)
        (bin_dir / "python").touch()

        result = state._get_hermes_python()
        expected = (tmp_hermes_home / ".venv" / "Scripts" / "python").resolve()
        assert str(Path(result).resolve()) == str(expected)
