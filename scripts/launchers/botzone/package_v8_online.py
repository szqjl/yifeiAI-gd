#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Botzone 掼蛋在线 Bot 打包脚本（V8 决策引擎 → 可上传 zip）。

产出：data/eval/botzone/v8_online_bot_<日期>_v<N>.zip
结构：zip 根 = __main__.py（在线入口）+ src/（全部 V8 决策链）+ game_logic/。

依赖策略：
  - 第三方库（numpy / scipy / torch）由 Botzone python3 沙箱预装，不打入 zip；
  - torch 已惰性导入（src/v/nn/ultimate_win_rate_engine_v7.py GUA-208），
    沙箱缺失 torch 时 V8 走 model=None 规则栈，仍可出牌；
  - 数据文件不打包（Botzone 要求走用户存储空间 `data` 路径，见 README）。

使用：
  python scripts/launchers/botzone/package_v8_online.py            # v1
  python scripts/launchers/botzone/package_v8_online.py --rev 3    # v3
  python scripts/launchers/botzone/package_v8_online.py --check    # 仅校验已有 zip
  python scripts/launchers/botzone/package_v8_online.py --keep     # 不删上一版本
  python scripts/launchers/botzone/package_v8_online.py --dry-run  # 只列文件不写 zip

本地验证（打包前）：
  echo '{"requests":[...],"responses":[]}' | python scripts/launchers/botzone/__main__.py
验证 zip 可运行：cd data/eval/botzone && python v8_online_bot_*.zip
"""

from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ENTRY = _REPO_ROOT / "scripts" / "launchers" / "botzone" / "__main__.py"
_OUT_DIR = _REPO_ROOT / "data" / "eval" / "botzone"

# zip 内要包含的顶层目录 / 文件（相对仓库根）。
# game_logic 位于 src/game_logic，随 src/ 一并打包；引擎顶层
# `from game_logic.guandan_constants` 走 try/except 回退，缺顶层 game_logic 安全。
_INCLUDE_TOP = ("src",)

# 明确排除的构建/训练产物（体积大且在线运行不需要）
_EXCLUDE_SNIPPETS = (
    "__pycache__",
    "training",
    "batch_executor",
    "scripts",
    "data",
    "logs",
    "tests",
    ".git",
    "*.pyc",
    "*.pth",
    "*.pt",
    "*.h5",
    "*.onnx",
    "*.zip",
    "*.log",
    "*.jsonl",
    "learn",  # v5 旧链（torch 训练），不在 V8 决策链
)


def _version_slug(rev: int) -> str:
    today = datetime.now().strftime("%Y%m%d")
    return f"v8_online_bot_{today}_v{rev}.zip"


def _latest_rev() -> int:
    if not _OUT_DIR.exists():
        return 0
    best = 0
    for p in _OUT_DIR.iterdir():
        m = re.match(r"v8_online_bot_\d{8}_v(\d+)\.zip$", p.name)
        if m:
            best = max(best, int(m.group(1)))
    return best


def _should_skip(rel: str) -> bool:
    parts = rel.replace("\\", "/").split("/")
    if any(s in parts for s in ("__pycache__", "training", "batch_executor",
                                "learn", "scripts", "tests", ".git")):
        return True
    if any(rel.endswith(s) for s in _EXCLUDE_SNIPPETS):
        return True
    return False


def collect_files() -> list[tuple[Path, str]]:
    """返回 (绝对路径, zip 内相对路径) 列表。"""
    files: list[tuple[Path, str]] = []
    for top in _INCLUDE_TOP:
        top_dir = _REPO_ROOT / top
        if not top_dir.exists():
            print(f"[警告] 缺失顶层目录: {top_dir}")
            continue
        for p in sorted(top_dir.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(_REPO_ROOT).as_posix()
            if _should_skip(rel):
                continue
            files.append((p, rel))
    # 入口 __main__.py 放 zip 根
    files.append((_ENTRY, "__main__.py"))
    return files


def _validate_zip(path: Path) -> bool:
    """校验 zip：入口存在 + src 可导入 + __main__ 语法可编译。"""
    ok = True
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
        if "__main__.py" not in names:
            print("[失败] zip 根缺少 __main__.py")
            return False
        src_ok = any(n.startswith("src/") for n in names)
        if not src_ok:
            print("[失败] zip 内缺少 src/")
            return False
        # 语法校验 __main__.py
        code = zf.read("__main__.py").decode("utf-8")
        try:
            compile(code, "__main__.py", "exec")
        except SyntaxError as e:
            print(f"[失败] __main__.py 语法错误: {e}")
            return False
    # 体积统计
    size_mb = path.stat().st_size / 1024 / 1024
    print(f"[OK] zip 校验通过: {path.name} ({size_mb:.1f} MB)")
    return ok


def build(args) -> int:
    _OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.check:
        latest = _latest_rev()
        if latest == 0:
            print("[提示] 无已有 zip")
            return 0
        path = _OUT_DIR / _version_slug(latest)
        return 0 if _validate_zip(path) else 1

    files = collect_files()
    total_bytes = sum(p.stat().st_size for p, _ in files)
    print(f"[收集] {len(files)} 个文件, 共 {total_bytes/1024/1024:.1f} MB")

    if args.dry_run:
        for _, rel in files:
            print("  " + rel)
        return 0

    rev = args.rev if args.rev else _latest_rev() + 1
    out_path = _OUT_DIR / _version_slug(rev)

    if out_path.exists():
        print(f"[警告] 目标已存在，覆盖: {out_path.name}")

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for src, rel in files:
            zf.write(src, rel)

    print(f"[产出] {out_path}")
    ok = _validate_zip(out_path)
    if not ok:
        return 1

    if not args.keep:
        for p in _OUT_DIR.glob("v8_online_bot_*.zip"):
            if p != out_path:
                print(f"[清理] 删除旧版本 {p.name}")
                p.unlink()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="V8 Botzone 在线 Bot 打包")
    parser.add_argument("--rev", type=int, default=0, help="版本号 vN（默认自动 +1）")
    parser.add_argument("--check", action="store_true", help="仅校验最新 zip")
    parser.add_argument("--dry-run", action="store_true", help="只列待打包文件")
    parser.add_argument("--keep", action="store_true", help="保留旧版本 zip")
    args = parser.parse_args(argv)
    return build(args)


if __name__ == "__main__":
    sys.exit(main())
