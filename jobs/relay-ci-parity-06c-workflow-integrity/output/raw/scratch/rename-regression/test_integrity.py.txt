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
