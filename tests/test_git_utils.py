"""Tests for fabricium.git_utils."""

import subprocess

import pytest

from fabricium import git_utils


class TestIsGitRepo:
    def test_returns_true_for_git_repo(self, tmp_git_repo):
        assert git_utils.is_git_repo(str(tmp_git_repo)) is True

    def test_returns_false_for_non_git_dir(self, tmp_path):
        assert git_utils.is_git_repo(str(tmp_path)) is False

    def test_defaults_to_cwd(self, tmp_git_repo, monkeypatch):
        monkeypatch.chdir(tmp_git_repo)
        assert git_utils.is_git_repo() is True


class TestGetHeadHash:
    def test_returns_non_empty_sha(self, tmp_git_repo):
        sha = git_utils.get_head_hash(str(tmp_git_repo))
        assert len(sha) == 40
        assert all(c in "0123456789abcdef" for c in sha)

    def test_raises_for_non_git_dir(self, tmp_path):
        with pytest.raises(subprocess.CalledProcessError):
            git_utils.get_head_hash(str(tmp_path))


class TestGetLocalHead:
    def test_head_is_same_as_get_head_hash(self, tmp_git_repo):
        repo = str(tmp_git_repo)
        assert git_utils.get_local_head(repo) == git_utils.get_head_hash(repo)

    def test_returns_none_for_missing_ref(self, tmp_git_repo):
        assert git_utils.get_local_head(str(tmp_git_repo), ref="nonexistent") is None

    def test_returns_none_for_non_git_dir(self, tmp_path):
        assert git_utils.get_local_head(str(tmp_path)) is None


class TestGetDiff:
    def test_returns_empty_for_no_changes(self, tmp_git_repo):
        sha = git_utils.get_head_hash(str(tmp_git_repo))
        diff = git_utils.get_diff(sha, "HEAD", str(tmp_git_repo))
        assert diff == ""

    def test_detects_new_file(self, tmp_git_repo):
        repo = str(tmp_git_repo)
        sha1 = git_utils.get_head_hash(repo)
        # Create a new file and commit
        (tmp_git_repo / "new.txt").write_text("hello")
        subprocess.run(["git", "add", "new.txt"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "add new.txt"], cwd=repo, check=True, capture_output=True
        )
        diff = git_utils.get_diff(sha1, "HEAD", repo)
        assert "new.txt" in diff
        assert "hello" in diff


class TestGetDiffStat:
    def test_returns_list_for_commit_with_changes(self, tmp_git_repo):
        repo = str(tmp_git_repo)
        sha1 = git_utils.get_head_hash(repo)
        (tmp_git_repo / "data.csv").write_text("a,b,c\n")
        subprocess.run(["git", "add", "data.csv"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "add data"], cwd=repo, check=True, capture_output=True
        )
        files = git_utils.get_diff_stat(sha1, "HEAD", repo)
        assert len(files) >= 1
        stat = files[0]
        assert "path" in stat
        assert "additions" in stat
        assert "deletions" in stat


class TestGetRemoteUrl:
    def test_returns_empty_for_no_remote(self, tmp_git_repo):
        assert git_utils.get_remote_url(str(tmp_git_repo)) == ""


class TestFetchRemote:
    def test_fails_for_no_remote(self, tmp_git_repo):
        result = git_utils.fetch_remote(str(tmp_git_repo))
        assert result["success"] is False


class TestGetDefaultBranch:
    def test_falls_back_to_main(self, tmp_git_repo):
        # No remote HEAD set, should fall back
        branch = git_utils.get_default_branch(str(tmp_git_repo))
        assert branch == "main"


class TestGetAheadBehind:
    def test_returns_zero_for_no_remote(self, tmp_git_repo):
        info = git_utils.get_ahead_behind(str(tmp_git_repo))
        assert info["ahead"] == 0
        assert info["behind"] == 0

    def test_detects_ahead_commits(self, tmp_git_repo_with_remote):
        repo, _remote_url = tmp_git_repo_with_remote
        repo_str = str(repo)
        # Make a new commit locally (ahead of remote)
        (repo / "local.txt").write_text("local change")
        subprocess.run(["git", "add", "local.txt"], cwd=repo_str, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "local change"],
            cwd=repo_str,
            check=True,
            capture_output=True,
        )
        info = git_utils.get_ahead_behind(repo_str)
        assert info["ahead"] == 1
        assert info["behind"] == 0


class TestIsAncestor:
    def test_same_commit_is_ancestor(self, tmp_git_repo):
        sha = git_utils.get_head_hash(str(tmp_git_repo))
        assert git_utils.is_ancestor(sha, sha, str(tmp_git_repo)) is True

    def test_parent_is_ancestor_of_child(self, tmp_git_repo):
        repo = str(tmp_git_repo)
        sha1 = git_utils.get_head_hash(repo)
        (tmp_git_repo / "child.txt").write_text("child")
        subprocess.run(["git", "add", "child.txt"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "child"], cwd=repo, check=True, capture_output=True)
        sha2 = git_utils.get_head_hash(repo)
        assert git_utils.is_ancestor(sha1, sha2, repo) is True
        # Reverse is False
        assert git_utils.is_ancestor(sha2, sha1, repo) is False

    def test_unrelated_returns_false(self, tmp_git_repo):
        assert git_utils.is_ancestor("0" * 40, "1" * 40, str(tmp_git_repo)) is False


class TestPullBranch:
    def test_fails_for_no_remote(self, tmp_git_repo):
        result = git_utils.pull_branch(str(tmp_git_repo))
        assert result["success"] is False


class TestStageAll:
    def test_stages_new_files(self, tmp_git_repo):
        repo = str(tmp_git_repo)
        (tmp_git_repo / "staged.txt").write_text("content")
        git_utils.stage_all(repo)
        status = subprocess.check_output(
            ["git", "-C", repo, "status", "--porcelain"], text=True
        ).strip()
        assert "staged.txt" in status


class TestCommit:
    def test_commits_staged_changes(self, tmp_git_repo):
        repo = str(tmp_git_repo)
        (tmp_git_repo / "to_commit.txt").write_text("committed")
        subprocess.run(["git", "add", "to_commit.txt"], cwd=repo, check=True, capture_output=True)
        result = git_utils.commit("test commit", repo)
        assert result["success"] is True

    def test_fails_without_staged_changes(self, tmp_git_repo):
        result = git_utils.commit("nothing to commit", str(tmp_git_repo))
        assert result["success"] is False
