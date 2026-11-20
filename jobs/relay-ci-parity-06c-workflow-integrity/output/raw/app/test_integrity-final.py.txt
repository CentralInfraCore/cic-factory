"""Regression tests for protected-path matching (scratch repo, no network)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import integrity  # noqa: E402

PROTECTED = [".github/", "scripts/", "policy.json"]


def f(status, filename, previous=None, sha="abc"):
    d = {"status": status, "filename": filename, "sha": sha}
    if previous:
        d["previous_filename"] = previous
    return d


class ProtectedChanges(unittest.TestCase):
    def test_plain_unprotected_is_unchanged(self):
        self.assertEqual(integrity.protected_changes([f("modified", "docs/a.md")], PROTECTED), [])

    def test_plain_protected_is_reported(self):
        self.assertEqual(len(integrity.protected_changes([f("modified", "scripts/check.sh")], PROTECTED)), 1)

    def test_rename_out_of_protected_dir_is_reported(self):
        # PR20 defect: destination unprotected, source protected -> was UNCHANGED
        r = integrity.protected_changes([f("renamed", "notes/ci.yml", ".github/workflows/ci.yml")], PROTECTED)
        self.assertEqual(len(r), 1)
        self.assertIn(".github/workflows/ci.yml", r[0])
        self.assertIn("notes/ci.yml", r[0])

    def test_rename_into_protected_dir_is_reported(self):
        r = integrity.protected_changes([f("renamed", "scripts/x.sh", "docs/x.sh")], PROTECTED)
        self.assertEqual(len(r), 1)

    def test_rename_between_unprotected_is_unchanged(self):
        self.assertEqual(integrity.protected_changes([f("renamed", "b/a.md", "a/a.md")], PROTECTED), [])

    def test_digest_binds_both_names(self):
        a = integrity.protected_changes([f("renamed", "notes/x", ".github/a")], PROTECTED)
        b = integrity.protected_changes([f("renamed", "notes/x", ".github/b")], PROTECTED)
        self.assertNotEqual(a, b)

    def test_no_previous_filename_key_is_safe(self):
        self.assertEqual(len(integrity.protected_changes([f("added", "policy.json")], PROTECTED)), 1)


if __name__ == "__main__":
    unittest.main()


class LoadChangeset(unittest.TestCase):
    """Completeness of the changed-file list (P0: truncated input must never produce SUCCESS)."""

    HEAD = "a" * 40

    @staticmethod
    def make(n_expected, n_listed, head=None, fail_on_page=None, pr_fails=False):
        head = head or LoadChangeset.HEAD
        listed = [{"status": "added", "filename": f"notes/f{i:05d}", "sha": "s"} for i in range(n_listed)]

        def get_pr():
            if pr_fails:
                raise RuntimeError("api down")
            return {"head": {"sha": head}, "changed_files": n_expected}

        def get_page(n):
            if fail_on_page == n:
                raise RuntimeError("page failed")
            return listed[(n - 1) * 100:n * 100]

        return get_pr, get_page

    def ok(self, n):
        files = integrity.load_changeset(*self.make(n, n), self.HEAD)
        self.assertEqual(len(files), n)

    def bad(self, *a, **k):
        with self.assertRaises(integrity.IncompleteChangeset):
            integrity.load_changeset(*self.make(*a, **k), self.HEAD)

    def test_2999_complete_is_accepted(self):
        self.ok(2999)

    def test_normal_small_is_accepted(self):
        self.ok(3)

    def test_empty_is_accepted(self):
        self.ok(0)

    def test_100_exact_page_boundary_is_accepted(self):
        self.ok(100)

    def test_3000_reaches_api_limit(self):
        self.bad(3000, 3000)

    def test_3001_denied(self):
        self.bad(3001, 3000)

    def test_3002_with_truncated_list_denied(self):
        self.bad(3002, 3000)

    def test_count_mismatch_denied(self):
        self.bad(5, 4)

    def test_more_listed_than_counted_denied(self):
        self.bad(4, 5)

    def test_paging_error_denied(self):
        self.bad(250, 250, fail_on_page=2)

    def test_pr_lookup_error_denied(self):
        self.bad(3, 3, pr_fails=True)

    def test_head_moved_denied(self):
        self.bad(3, 3, head="b" * 40)

    def test_missing_counter_denied(self):
        with self.assertRaises(integrity.IncompleteChangeset):
            integrity.load_changeset(lambda: {"head": {"sha": self.HEAD}}, lambda n: [], self.HEAD)
