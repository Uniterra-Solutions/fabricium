"""Tests for fabricium.state."""

import os

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


def test_get_global_hermes_home_default():
    """Without HERMES_HOME set, defaults to ~/.hermes."""
    old = os.environ.get("HERMES_HOME")
    try:
        os.environ.pop("HERMES_HOME", None)
        result = state._get_global_hermes_home()
        assert result.name == ".hermes"
    finally:
        if old is not None:
            os.environ["HERMES_HOME"] = old


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
