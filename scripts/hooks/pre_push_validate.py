#!/usr/bin/env python3
"""推送前校验：Layer 2 大文件、禁止推 main。供 pre_push_check.bat 与 pre-push 钩子共用。"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MAX_BYTES = 1024 * 1024
LAYER2_MARKERS = (
    "models/",
    "logs/",
    "game_records/",
    "training_logs/",
    "data/artifacts/",
)
LAYER2_SUFFIXES = (".pth", ".pkl", ".h5")
LAYER2_BASENAMES = {"game_scores_m2.json", "execution_state.json"}


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def current_branch() -> str:
    r = _run("git", "rev-parse", "--abbrev-ref", "HEAD")
    return (r.stdout or "").strip()


def staged_files() -> list[str]:
    r = _run("git", "diff", "--cached", "--name-only", "--diff-filter=ACMR")
    return [ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip()]


def push_range_files(local_sha: str, remote_sha: str) -> list[str]:
    if not remote_sha or set(remote_sha) <= {"0"}:
        r = _run("git", "log", "--name-only", "--pretty=format:", f"{remote_sha}..{local_sha}")
    else:
        r = _run("git", "diff", "--name-only", remote_sha, local_sha)
    return [ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip()]


def is_layer2_violation(path: str) -> bool:
    norm = path.replace("\\", "/")
    base = os.path.basename(norm)
    if base in LAYER2_BASENAMES:
        return True
    if any(norm.startswith(m) or f"/{m}" in f"/{norm}" for m in LAYER2_MARKERS):
        return True
    return norm.endswith(LAYER2_SUFFIXES)


def check_files(files: list[str], label: str) -> list[str]:
    bad: list[str] = []
    for rel in files:
        full = REPO_ROOT / rel
        if not full.is_file():
            continue
        size = full.stat().st_size
        if size > MAX_BYTES or is_layer2_violation(rel):
            bad.append(f"{rel} ({size / 1024 / 1024:.2f} MB)")
    if bad:
        print(f"\n❌ {label} 发现问题 ({len(bad)} 个):")
        for item in bad[:20]:
            print(f"   - {item}")
        if len(bad) > 20:
            print(f"   ... 另有 {len(bad) - 20} 个")
    else:
        print(f"  ✓ {label} 通过")
    return bad


def check_branch_for_push(remote_ref: str | None = None) -> int:
    branch = current_branch()
    if branch == "main":
        print("❌ 当前在 main 分支。治理方案：日常开发用 m-dev。")
        print("   见 docs/governance/main-branch-policy.md")
        return 1
    if remote_ref and (remote_ref.endswith("/main") or remote_ref == "refs/heads/main"):
        print("❌ 禁止向 origin/main 推送。")
        print("   见 docs/governance/main-branch-policy.md")
        return 1
    print(f"  ✓ 分支 {branch}（非 main）")
    return 0


def run_staged_check() -> int:
    print("=" * 60)
    print("推送前校验（治理 Layer 2 + 分支）")
    print("=" * 60)
    print("\nAgent 须已读: docs/governance/M-V-Series-治理方案.md §4/§6/§8")
    print("清单: docs/guandan-brain/AGENT_PUSH_CHECKLIST.md\n")

    rc = check_branch_for_push()
    if rc:
        return rc

    bad = check_files(staged_files(), "暂存区")
    return 1 if bad else 0


def run_hook(stdin_text: str) -> int:
    """pre-push 钩子：解析 stdin，检查 outgoing commits。"""
    lines = [ln for ln in stdin_text.splitlines() if ln.strip()]
    rc = 0
    i = 0
    while i < len(lines):
        local_ref = lines[i]
        local_sha = lines[i + 1] if i + 1 < len(lines) else ""
        remote_ref = lines[i + 2] if i + 2 < len(lines) else ""
        remote_sha = lines[i + 3] if i + 3 < len(lines) else ""
        i += 4

        if check_branch_for_push(remote_ref):
            rc = 1
            continue
        if local_sha:
            bad = check_files(
                push_range_files(local_sha, remote_sha),
                f"待推送 {local_ref} -> {remote_ref}",
            )
            if bad:
                rc = 1

    if rc:
        print("\n推送已阻止。修复后重试，或阅读 AGENT_PUSH_CHECKLIST.md。")
    return rc


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="推送前治理校验")
    parser.add_argument(
        "--hook",
        action="store_true",
        help="Git pre-push 模式（从 stdin 读取 ref 列表）",
    )
    args = parser.parse_args()
    if args.hook:
        return run_hook(sys.stdin.read())
    return run_staged_check()


if __name__ == "__main__":
    sys.exit(main())
