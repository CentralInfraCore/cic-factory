#!/usr/bin/env python3
"""docs.link-check — verify that relative markdown links in docs/ and the
top-level READMEs resolve to files that exist in the repository.

Stdlib-only (no project.schema.yaml / compiler / infra dependencies). Used by
`make docs.link-check` and the CI `docs.link-check` step.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Markdown link target, e.g. [text](path/to/file.md) or [text](path#anchor).
LINK_RE = re.compile(r"\]\(([^)]+)\)")

DOC_GLOBS = ["docs/**/*.md", "README.md", "README.hu.md"]


def is_external_or_special(target: str) -> bool:
    if not target:
        return True
    if target.startswith(("http://", "https://", "mailto:", "#")):
        return True
    if "://" in target:
        return True
    return False


def check_file(md_file: Path) -> list[str]:
    errors = []
    text = md_file.read_text(encoding="utf-8")
    for match in LINK_RE.finditer(text):
        target = match.group(1).strip()
        if is_external_or_special(target):
            continue
        # Strip a trailing anchor (path/to/file.md#section).
        path_part = target.split("#", 1)[0]
        if not path_part:
            continue
        resolved = (md_file.parent / path_part).resolve()
        if not resolved.exists():
            errors.append(f"{md_file.relative_to(REPO_ROOT)}: broken link -> {target}")
    return errors


def main() -> int:
    all_errors: list[str] = []
    for pattern in DOC_GLOBS:
        for md_file in sorted(REPO_ROOT.glob(pattern)):
            all_errors.extend(check_file(md_file))

    if all_errors:
        print("docs.link-check: broken internal links found:")
        for err in all_errors:
            print(f"  {err}")
        return 1

    print("docs.link-check: OK — all internal markdown links resolve.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
