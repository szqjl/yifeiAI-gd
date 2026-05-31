#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""推送前 .gitignore 与暂存区大文件检查（见 docs/development/推送前检查指南.md）。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
MB = 1024 * 1024
LARGE_THRESHOLD = MB


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _git_out(*args: str) -> str:
    r = _git(*args)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or f"git {' '.join(args)} failed")
    return r.stdout.strip()


def _is_ignored(path: str) -> bool:
    return _git("check-ignore", "-q", path).returncode == 0


def _large_files(paths: list[str]) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for rel in paths:
        if not rel:
            continue
        p = REPO_ROOT / rel
        if not p.is_file():
            continue
        size = p.stat().st_size
        if size > LARGE_THRESHOLD:
            out.append((rel, size))
    return out


def main() -> int:
    ok = True
    print("=" * 60)
    print("verify_gitignore — 推送前检查")
    print("=" * 60)

    if not (REPO_ROOT / ".gitignore").is_file():
        print("❌ .gitignore 不存在")
        return 1
    print("✅ .gitignore 存在")

    staged = [ln for ln in _git_out("diff", "--cached", "--name-only").splitlines() if ln.strip()]
    staged_large = _large_files(staged)
    staged_models = [p for p in staged if p.replace("\\", "/").startswith("models/")]
    if staged_large:
        ok = False
        print(f"\n❌ 暂存区大文件 ({len(staged_large)}):")
        for path, size in staged_large[:10]:
            print(f"   {size / MB:.2f} MB — {path}")
    else:
        print("✅ 暂存区无 >1MB 文件")
    if staged_models:
        ok = False
        print(f"\n❌ 暂存区含 models/ 文件 ({len(staged_models)}):")
        for path in staged_models[:10]:
            print(f"   - {path}")
    else:
        print("✅ 暂存区无 models/ 文件")

    untracked = [
        ln[3:].strip()
        for ln in _git_out("status", "--porcelain").splitlines()
        if ln.startswith("??")
    ]
    bad_untracked: list[tuple[str, int]] = []
    for rel in untracked:
        p = REPO_ROOT / rel
        if not p.is_file():
            continue
        if p.stat().st_size <= LARGE_THRESHOLD:
            continue
        if _is_ignored(rel):
            continue
        bad_untracked.append((rel, p.stat().st_size))
    if bad_untracked:
        ok = False
        print(f"\n❌ 未跟踪且未忽略的大文件 ({len(bad_untracked)}):")
        for path, size in bad_untracked[:10]:
            print(f"   {size / MB:.2f} MB — {path}")
    else:
        print("✅ 未跟踪大文件均已忽略或不存在")

    tracked_models = _git_out("ls-files", "models/")
    if tracked_models:
        print("⚠️  历史 tracked models/ 文件仍存在（推送前勿 add）；本次暂存区未含 models/")
    else:
        print("✅ models/ 无被跟踪文件")

    print("\n" + ("✅ 检查通过" if ok else "❌ 检查未通过"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
