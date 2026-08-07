import os
import subprocess

# Add project root to sys.path
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from tools.releaselib.git_service import GitService, GitServiceError, GitStateError


@pytest.fixture
def git_service():
    """Fixture to create a GitService instance."""
    return GitService(cwd="/fake/repo", timeout=30)


@patch("subprocess.run")
def test_run_success(mock_run, git_service):
    """Test a successful run of a git command."""
    mock_run.return_value = MagicMock(stdout=b"ok", stderr=b"", returncode=0)
    result = git_service.run(["git", "status"])
    assert result == "ok"
    mock_run.assert_called_once_with(
        ["git", "status"],
        capture_output=True,
        check=True,
        cwd=Path("/fake/repo"),
        timeout=30,
    )


@patch("subprocess.run")
def test_run_called_process_error(mock_run, git_service):
    """Test that CalledProcessError is wrapped in GitServiceError."""
    mock_run.side_effect = subprocess.CalledProcessError(
        1, "git", stderr=b"error message"
    )
    with pytest.raises(
        GitServiceError, match="Git command failed: git status\nerror message"
    ):
        git_service.run(["git", "status"])


@patch("subprocess.run")
def test_run_file_not_found_error(mock_run, git_service):
    """Test that FileNotFoundError is wrapped in GitServiceError."""
    mock_run.side_effect = FileNotFoundError("git not found")
    with pytest.raises(
        GitServiceError,
        match="Git command not found: git status. Is Git installed and in your PATH?",
    ):
        git_service.run(["git", "status"])


@patch("subprocess.run")
def test_run_timeout_expired(mock_run, git_service):
    """Test that TimeoutExpired is wrapped in GitServiceError."""
    mock_run.side_effect = subprocess.TimeoutExpired("git status", 30)
    with pytest.raises(
        GitServiceError, match="Git command timed out after 30 seconds: git status"
    ):
        git_service.run(["git", "status"])


@patch.object(GitService, "run")
def test_get_current_branch(mock_run, git_service):
    mock_run.return_value = "main"
    assert git_service.get_current_branch() == "main"
    mock_run.assert_called_once_with(["git", "rev-parse", "--abbrev-ref", "HEAD"])


@patch.object(GitService, "run")
def test_get_status_porcelain(mock_run, git_service):
    mock_run.return_value = "M  file.txt"
    assert git_service.get_status_porcelain() == "M  file.txt"
    mock_run.assert_called_once_with(["git", "status", "--porcelain"])


@patch.object(GitService, "get_status_porcelain")
def test_is_dirty_true(mock_get_status_porcelain, git_service):
    """Test is_dirty when there are uncommitted changes."""
    mock_get_status_porcelain.return_value = "M file.txt"
    assert git_service.is_dirty() is True


@patch.object(GitService, "get_status_porcelain")
def test_is_dirty_false(mock_get_status_porcelain, git_service):
    """Test is_dirty when there are no uncommitted changes."""
    mock_get_status_porcelain.return_value = ""
    assert git_service.is_dirty() is False


@patch("subprocess.run")
def test_is_index_dirty_true(mock_run, git_service):
    """Test is_index_dirty when there are staged changes."""
    mock_run.side_effect = subprocess.CalledProcessError(1, "git diff-index")
    assert git_service.is_index_dirty() is True


@patch("subprocess.run")
def test_is_index_dirty_false(mock_run, git_service):
    """Test is_index_dirty when there are no staged changes."""
    mock_run.return_value = MagicMock(returncode=0)
    assert git_service.is_index_dirty() is False


@patch("subprocess.run")
def test_is_index_dirty_file_not_found(mock_run, git_service):
    """Test is_index_dirty raises GitServiceError on FileNotFoundError."""
    mock_run.side_effect = FileNotFoundError("git not found")
    with pytest.raises(GitServiceError, match="Failed to check Git index status"):
        git_service.is_index_dirty()


@patch("subprocess.run")
def test_is_index_dirty_timeout_expired(mock_run, git_service):
    """Test is_index_dirty raises GitServiceError on TimeoutExpired."""
    mock_run.side_effect = subprocess.TimeoutExpired("git diff-index", 30)
    with pytest.raises(GitServiceError, match="Failed to check Git index status"):
        git_service.is_index_dirty()


@patch.object(GitService, "run")
def test_get_tags(mock_run, git_service):
    mock_run.return_value = "v1.0.0\nv1.1.0\n"
    assert git_service.get_tags() == ["v1.0.0", "v1.1.0"]
    mock_run.assert_called_once_with(["git", "tag", "--list"])


@patch.object(GitService, "run")
def test_get_tags_with_pattern(mock_run, git_service):
    mock_run.return_value = "v1.1.0"
    assert git_service.get_tags(pattern="v1.1.*") == ["v1.1.0"]
    mock_run.assert_called_once_with(["git", "tag", "--list", "v1.1.*"])


@patch.object(GitService, "run")
def test_write_tree(mock_run, git_service):
    mock_run.return_value = "some_tree_id"
    assert git_service.write_tree() == "some_tree_id"
    mock_run.assert_called_once_with(["git", "write-tree"])


@patch.object(GitService, "run")
def test_add(mock_run, git_service):
    file_path = Path("a/b/c.txt")
    git_service.add(file_path)
    mock_run.assert_called_once_with(["git", "add", file_path])


@patch.object(GitService, "_run_raw")
def test_archive_tree_bytes(mock_run_raw, git_service):
    mock_run_raw.return_value = b"archive content"
    result = git_service.archive_tree_bytes("some_tree_id", prefix="./")
    assert result == b"archive content"
    mock_run_raw.assert_called_once_with(
        ["git", "archive", "--format=tar", "--prefix=./", "some_tree_id"]
    )


@patch("subprocess.run")
def test_assert_clean_index_is_clean(mock_run, git_service):
    """Test assert_clean_index when index is clean."""
    mock_run.return_value = MagicMock(returncode=0)
    try:
        git_service.assert_clean_index()
    except GitStateError:
        pytest.fail("assert_clean_index raised GitStateError unexpectedly.")


@patch("subprocess.run")
def test_assert_clean_index_is_dirty(mock_run, git_service):
    """Test assert_clean_index when index has staged changes."""
    mock_run.return_value = MagicMock(returncode=1)
    with pytest.raises(GitStateError, match="Staged changes detected"):
        git_service.assert_clean_index()


@patch("subprocess.run")
def test_assert_clean_index_git_error(mock_run, git_service):
    """Test assert_clean_index with a generic git error."""
    mock_run.return_value = MagicMock(returncode=128, stderr=b"git error")
    with pytest.raises(GitServiceError, match="Git command failed with exit code 128"):
        git_service.assert_clean_index()


@patch("subprocess.run")
def test_assert_clean_index_timeout(mock_run, git_service):
    """Test assert_clean_index with a timeout."""
    mock_run.side_effect = subprocess.TimeoutExpired("git diff-index", 30)
    with pytest.raises(GitServiceError, match="Git command timed out"):
        git_service.assert_clean_index()


@patch("subprocess.run")
def test_assert_clean_index_file_not_found(mock_run, git_service):
    """Test assert_clean_index raises GitServiceError on FileNotFoundError."""
    mock_run.side_effect = FileNotFoundError("git not found")
    with pytest.raises(GitServiceError, match="Git command not found"):
        git_service.assert_clean_index()


@patch.object(GitService, "run")
def test_checkout(mock_run, git_service):
    git_service.checkout("my-branch")
    mock_run.assert_called_once_with(["git", "checkout", "my-branch"])


@patch.object(GitService, "run")
def test_checkout_new_branch(mock_run, git_service):
    git_service.checkout("new-branch", create_new=True)
    mock_run.assert_called_once_with(["git", "checkout", "-b", "new-branch"])


@patch.object(GitService, "run")
def test_create_branch(mock_run, git_service):
    git_service.create_branch("another-branch")
    mock_run.assert_called_once_with(["git", "branch", "another-branch"])


@patch.object(GitService, "run")
def test_delete_branch(mock_run, git_service):
    git_service.delete_branch("old-branch")
    mock_run.assert_called_once_with(["git", "branch", "-d", "old-branch"])


@patch.object(GitService, "run")
def test_delete_branch_force(mock_run, git_service):
    git_service.delete_branch("old-branch", force=True)
    mock_run.assert_called_once_with(["git", "branch", "-D", "old-branch"])


@patch.object(GitService, "run")
def test_merge(mock_run, git_service):
    git_service.merge("feature-branch")
    mock_run.assert_called_once_with(["git", "merge", "feature-branch"])


@patch.object(GitService, "run")
def test_merge_no_ff(mock_run, git_service):
    git_service.merge("feature-branch", no_ff=True)
    mock_run.assert_called_once_with(["git", "merge", "--no-ff", "feature-branch"])


@patch.object(GitService, "run")
def test_merge_with_message(mock_run, git_service):
    git_service.merge("feature-branch", message="Merge message")
    mock_run.assert_called_once_with(
        ["git", "merge", "-m", "Merge message", "feature-branch"]
    )
