"""Shared pytest fixtures for fabricium tests."""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# ── Ensure local src/ takes priority over any PYTHONPATH entries ──────────
# Hermes desktop sets PYTHONPATH to its own venv site-packages, which
# may contain an older installed copy of fabricium that shadows the
# local editable install.  Push the project source root to the front
# of sys.path so tests always run against the working tree.
#
# This MUST happen at module level in conftest.py because pytest loads
# conftest before collecting (importing) test files.
_SRC = Path(__file__).absolute().parent.parent / "src"
sys.path.insert(0, str(_SRC))
# Hermes PYTHONPATH may have caused fabricium to be imported from the
# wrong location before conftest ran.  Purge all fabricium modules
# so the next import picks up the local src/ tree.
_fabricium_keys = [k for k in sys.modules if k == "fabricium" or k.startswith("fabricium.")]
for _k in _fabricium_keys:
    del sys.modules[_k]
del _SRC
# ───────────────────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_git_repo():
    """Create a temporary git repository with one initial commit.

    Yields the Path to the repo. Cleans up after the test.
    """
    tmp = tempfile.mkdtemp()
    repo = Path(tmp)
    try:
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        # Create initial commit
        (repo / "README.md").write_text("initial")
        subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "initial commit"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        yield repo
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def tmp_git_repo_with_remote(tmp_git_repo):
    """Create a git repo with a local 'remote' and one extra commit on main.

    Yields (repo_path, remote_url).
    """
    repo = tmp_git_repo

    # Create a bare remote repo
    remote_dir = tempfile.mkdtemp()
    remote_path = Path(remote_dir)
    try:
        subprocess.run(
            ["git", "init", "--bare"],
            cwd=remote_path,
            check=True,
            capture_output=True,
        )
        # Add as origin
        subprocess.run(
            ["git", "remote", "add", "origin", str(remote_path)],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        # Push main
        subprocess.run(
            ["git", "push", "-u", "origin", "main"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        # Set up remote HEAD
        subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        yield repo, str(remote_path)
    finally:
        shutil.rmtree(remote_dir, ignore_errors=True)


@pytest.fixture
def tmp_hermes_home():
    """Create a temporary fake ~/.hermes directory and set HERMES_HOME.

    Yields the Path. Cleans up after the test and restores env.
    """
    tmp = tempfile.mkdtemp()
    hermes_home = Path(tmp) / ".hermes"
    hermes_home.mkdir(parents=True)
    old_home = os.environ.get("HERMES_HOME")
    os.environ["HERMES_HOME"] = str(hermes_home)
    try:
        yield hermes_home
    finally:
        if old_home is not None:
            os.environ["HERMES_HOME"] = old_home
        else:
            os.environ.pop("HERMES_HOME", None)
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def tmp_plugin_dir(tmp_hermes_home):
    """Create a temporary plugin directory with skills/ and SOUL.md.

    Yields the plugin_dir Path.
    """
    plugin_dir = tmp_hermes_home / "plugins" / "test-plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "SOUL.md").write_text("# Test Agent\n\nThis is a test SOUL.md.\n")

    # Create a skills/ directory with two skills
    skills_dir = plugin_dir / "skills"
    skills_dir.mkdir()
    for name in ("skill-a", "skill-b"):
        skill_dir = skills_dir / name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(f"---\nname: {name}\n---\n# {name}\n\nTest skill.\n")

    # Create global skills dir
    (tmp_hermes_home / "skills").mkdir(parents=True)

    return plugin_dir
