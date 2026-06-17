# -*- coding: utf-8 -*-
"""Fail if deprecated doc paths reappear in tracked text files."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DEPRECATED = [
    re.compile(r"docs/claude-analysis/"),
    re.compile(r"docs/competition/lalala/lalala_src/.*\.py"),
    re.compile(r"(?<![\w/])docs/rules/"),
    re.compile(r"(?<![\w/])docs/skill/"),
    re.compile(r"(?<![\w/])docs/implementation/"),
]

SKIP_PARTS = {".git", "__pycache__", "node_modules", ".idea"}
TEXT_SUFFIXES = {".md", ".py", ".mdc", ".sh", ".bat", ".yaml", ".yml", ".json", ".ps1"}
ALLOWLIST = {
    ROOT / "scripts/tools/migrate_docs_phase5f.py",
    ROOT / "scripts/tools/migrate_docs_phase5g.py",
    ROOT / "scripts/checks/check_doc_paths.py",
    ROOT / "docs/claude-analysis/README.md",
    ROOT / "docs/rules/README.md",
    ROOT / "docs/skill/README.md",
    ROOT / "docs/competition/lalala/lalala_src/README.md",
    ROOT / "docs/implementation/README.md",
    ROOT / "docs/governance/DOCUMENT_AUDIT.md",
    ROOT / "docs/governance/repo-cleanup-inventory.md",
    ROOT / "docs/governance/M-V-Series-治理方案.md",
    ROOT / "docs/governance/ROOT_ARTIFACT_AUDIT.md",
    ROOT / "docs/guandan-brain/ITERATIONS.md",
    ROOT / "docs/archive/README.md",
    ROOT / "reference/lalala/README.md",
}


def main() -> int:
    hits: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path in ALLOWLIST:
            continue
        if any(p in SKIP_PARTS for p in path.parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for pat in DEPRECATED:
            if pat.search(text):
                hits.append(f"{path.relative_to(ROOT)}: {pat.pattern}")
                break
    if hits:
        print("Deprecated doc paths found:")
        for h in hits:
            print(" ", h)
        return 1
    print("check_doc_paths: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
