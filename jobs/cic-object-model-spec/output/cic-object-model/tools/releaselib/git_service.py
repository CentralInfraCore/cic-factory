import subprocess  # nosec
from pathlib import Path
from typing import Optional

from .exceptions import GitServiceError, GitStateError


class GitService:
    """
    A service class to abstract Git command operations.
    This makes the core logic testable by allowing this service to be mocked.
    """

    def __init__(self, cwd=None, timeout=60):
        self.cwd = Path(cwd) if cwd else None
        self.timeout = timeout

    def _run_raw(self, command):
        """Runs a command and returns raw stdout bytes."""
        try:
            command_str = [str(c) if isinstance(c, Path) else c for c in command]
            result = subprocess.run(
                command_str,
                capture_output=True,
                check=True,
                cwd=self.cwd,
                timeout=self.timeout,
            )  # nosec
            return result.stdout
        except subprocess.CalledProcessError as e:
            cmd_display = " ".join(map(str, command))
            raise GitServiceError(
                f"Git command failed: {cmd_display}\n{e.stderr.decode('utf-8', errors='replace')}",
                cause=e,
            )
        except FileNotFoundError as e:
            cmd_display = " ".join(map(str, command))
            raise GitServiceError(
                f"Git command not found: {cmd_display}. Is Git installed and in your PATH?",
                cause=e,
            )
        except subprocess.TimeoutExpired as e:
            cmd_display = " ".join(map(str, command))
            raise GitServiceError(
                f"Git command timed out after {self.timeout} seconds: {cmd_display}",
                cause=e,
            )

    def run(self, command):
        """Runs a Git command and returns its stripped string output."""
        raw_output = self._run_raw(command)
        return raw_output.decode("utf-8", errors="replace").strip()

    def get_current_branch(self):
        """Returns the current active branch name."""
        return self.run(["git", "rev-parse", "--abbrev-ref", "HEAD"])

    def get_status_porcelain(self):
        """Returns the output of 'git status --porcelain'."""
        return self.run(["git", "status", "--porcelain"])

    def is_dirty(self):
        """Returns True if there are uncommitted changes."""
        return bool(self.get_status_porcelain())

    def is_index_dirty(self):
        """Returns True if there are staged changes in the index."""
        try:
            subprocess.run(
                ["git", "diff-index", "--quiet", "HEAD", "--"],
                check=True,
                capture_output=True,
                cwd=self.cwd,
                timeout=self.timeout,
            )  # nosec
            return False
        except subprocess.CalledProcessError:
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            raise GitServiceError(f"Failed to check Git index status: {e}") from e

    def get_tags(self, pattern=None):
        """Returns a list of tags, optionally filtered by a pattern."""
        command = ["git", "tag", "--list"]
        if pattern:
            command.append(pattern)
        raw_output = self.run(command)
        return [tag.strip() for tag in raw_output.split("\n") if tag.strip()]

    def write_tree(self):
        """Runs 'git write-tree' and returns the tree ID."""
        return self.run(["git", "write-tree"])

    def add(self, file_path: Path):
        """Stages a specific file."""
        return self.run(["git", "add", file_path])

    def archive_tree_bytes(self, tree_id, prefix=None):
        """Runs 'git archive' and returns the raw bytes of the tar archive."""
        command = ["git", "archive", "--format=tar"]
        if prefix:
            command.append(f"--prefix={prefix}")
        command.append(tree_id)
        return self._run_raw(command)

    def assert_clean_index(self):
        """
        Checks if the Git index is clean (no staged changes).
        Raises GitStateError if staged changes are detected.
        """
        try:
            result = subprocess.run(
                ["git", "diff-index", "--quiet", "HEAD", "--"],
                capture_output=True,
                check=False,
                cwd=self.cwd,
                timeout=self.timeout,
            )  # nosec
            if result.returncode == 1:
                raise GitStateError(
                    "Staged changes detected in Git index. Please commit them before releasing."
                )
            elif result.returncode != 0:
                raise GitServiceError(
                    f"Git command failed with exit code {result.returncode}: git diff-index\n{result.stderr.decode('utf-8', errors='replace')}"
                )
        except subprocess.TimeoutExpired as e:
            raise GitServiceError("Git command timed out: git diff-index", cause=e)
        except FileNotFoundError as e:
            raise GitServiceError("Git command not found. Is Git installed?", cause=e)

    def checkout(self, branch_name: str, create_new: bool = False):
        """Checks out a Git branch, optionally creating it."""
        command = ["git", "checkout"]
        if create_new:
            command.append("-b")
        command.append(branch_name)
        return self.run(command)

    def create_branch(self, branch_name: str):
        """Creates a new Git branch."""
        return self.run(["git", "branch", branch_name])

    def delete_branch(self, branch_name: str, force: bool = False):
        """Deletes a Git branch."""
        command = ["git", "branch", "-D" if force else "-d", branch_name]
        return self.run(command)

    def merge(
        self, branch_name: str, no_ff: bool = False, message: Optional[str] = None
    ):
        """Merges a Git branch into the current branch."""
        command = ["git", "merge"]
        if no_ff:
            command.append("--no-ff")
        if message:
            command.extend(["-m", message])
        command.append(branch_name)
        return self.run(command)
