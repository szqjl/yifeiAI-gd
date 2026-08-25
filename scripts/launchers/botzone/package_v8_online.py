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

py3.6 兼容（Botzone 沙箱 = Ubuntu 16.04 / Python 3.6，GUA-203）：
  - 剥离 `from __future__ import annotations`（PEP 563 是 3.7+ 语法，py3.6
    编译即 SyntaxError，曾导致 v8_5 上传后 RE）；
  - 将全部注解字符串化（等价 PEP 563 延迟求值），避免剥离 future import 后
    注解在 py3.6 函数定义时被求值——裸前向引用会 NameError、
    `List[..] | None`（PEP 604）会 TypeError（grouping_engine.py L1718/1719）。
  以上变换只作用于 zip 内产物，不改仓库源文件。

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
import ast
import fnmatch
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

# zip 内要包含的顶层目录 / 文件（相对仓库根，按 V7 决策链真实依赖收集）：
#   - src/v：V8 决策引擎（ultimate_win_rate_engine_v7 及 endgame/guards/features/stage_*）
#   - src/game_logic：组牌/牌型常量等底层（引擎顶层 `from game_logic.guandan_constants`
#     走 try/except 回退，但 src/game_logic 保留可避免回退到默认值）
#   - src/communication/botzone_adapter.py：在线 Bot 适配器（纯 stdlib，注入引擎）
# 刻意排除 src/train、src/m、src/rl_agent、src/communication 其余 yf* 适配器等非决策链内容。
_INCLUDE_TOP = ("src/v", "src/game_logic")
_INCLUDE_FILES = ("src/communication/botzone_adapter.py",)

# 明确排除的构建/训练产物（体积大且在线运行不需要）
_EXCLUDE_SNIPPETS = (
    "__pycache__",
    "training",
    "train",  # src/train 训练脚本（引擎仅注释引用，见 engine L473）
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
    "*.md",       # 在线运行不需要文档
    "*.backup",   # 备份/临时文件（平台解析可能失败）
    "*.backup_*", # .backup_YYYYMMDD_HHMMSS 备份
    "learn",      # v5 旧链（torch 训练），不在 V8 决策链
)


def _version_slug(rev: int) -> str:
    today = datetime.now().strftime("%Y%m%d")
    # 命名 v8_<N>：V8 引擎代号 + 构建序号（避免裸 v<N> 与引擎版本混淆）
    return f"v8_online_bot_{today}_v8_{rev}.zip"


def _latest_rev() -> int:
    if not _OUT_DIR.exists():
        return 0
    best = 0
    for p in _OUT_DIR.iterdir():
        m = re.match(r"v8_online_bot_\d{8}_v8_(\d+)\.zip$", p.name)
        if m:
            best = max(best, int(m.group(1)))
    return best


def _should_skip(rel: str) -> bool:
    parts = rel.replace("\\", "/").split("/")
    # 仅排除仓库根 src/train/（M3 训练脚本），保留 src/v/nn/training/bc_dataset 等推理切片
    if rel.startswith("src/train/"):
        return True
    if rel.startswith("src/v/nn/training/") and rel != "src/v/nn/training/bc_dataset.py":
        return True
    if any(s in parts for s in ("__pycache__", "batch_executor",
                                "learn", "scripts", "tests", ".git")):
        return True
    if any(fnmatch.fnmatch(rel, s) or rel.endswith(s) for s in _EXCLUDE_SNIPPETS):
        return True
    # .backup_YYYYMMDD_HHMMSS 这类备份：ext 含 "backup_" 前缀
    if ".backup" in rel.rsplit("/", 1)[-1]:
        return True
    # 孤立损坏文件（语法坏、无 import，平台编译会失败 → 上传"未知错误"）
    if rel == "src/game_logic/hand_combiner_patched.py":
        return True
    return False


def _py36_transform(src: str, filename: str) -> str:
    """py3.6 兼容变换：剥离 PEP563 future import + 注解字符串化。

    Botzone 沙箱 = Python 3.6（GUA-203）。`from __future__ import annotations`
    在 py3.6 编译即 SyntaxError，故剥离；剥离后注解会在函数定义时求值，
    裸前向引用（`List[GroupingPlan]` 未定义时）NameError、`List[..] | None`
    （PEP604）TypeError，故把注解改写为等价字符串字面量（延迟求值，等价 PEP563）。
    """
    # 1) 剥离 future import 行
    src = re.sub(r"(?m)^from __future__ import annotations[ \t]*\r?\n", "", src)

    # 2) 注解字符串化：用 ast 定位每个注解表达式，替换为字符串字面量
    try:
        tree = ast.parse(src, filename=filename)
    except SyntaxError:
        return src  # 语法错误留给 _validate_zip 报

    # 行首偏移表：1-indexed 行号 -> 0-based 字符偏移
    line_starts = [0]
    for line in src.splitlines(True):
        line_starts.append(line_starts[-1] + len(line))

    def to_offsets(node) -> tuple[int, int]:
        start = line_starts[node.lineno - 1] + node.col_offset
        end = line_starts[node.end_lineno - 1] + node.end_col_offset
        return start, end

    def expr_to_str(node) -> str:
        s, e = to_offsets(node)
        return src[s:e]

    spans: list[tuple[int, int, str]] = []

    def add_annotation(ann):
        if ann is None:
            return
        # 已是字符串注解/常量则跳过
        if isinstance(ann, ast.Constant) and isinstance(ann.value, str):
            return
        s, e = to_offsets(ann)
        text = expr_to_str(ann)
        spans.append((s, e, text))

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            add_annotation(node.returns)
            for a in list(node.args.posonlyargs) + list(node.args.args) \
                     + list(node.args.kwonlyargs):
                add_annotation(a.annotation)
            if node.args.vararg:
                add_annotation(node.args.vararg.annotation)
            if node.args.kwarg:
                add_annotation(node.args.kwarg.annotation)
        elif isinstance(node, ast.AnnAssign):
            add_annotation(node.annotation)

    # 从后往前替换，避免偏移失效；注解转 JSON 双引号字符串（转义安全）
    out = src
    for s, e, text in sorted(spans, key=lambda x: -x[0]):
        quoted = json.dumps(text, ensure_ascii=True)
        out = out[:s] + quoted + out[e:]
    return out


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
    for rel in _INCLUDE_FILES:
        p = _REPO_ROOT / rel
        if not p.exists():
            print(f"[警告] 缺失文件: {p}")
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
        # 所有含 .py 的包目录都必须有 __init__.py：py3.6 的 zipimport 不支持
        # PEP420 命名空间包，缺则 `import src` / `import src.communication`
        # 在平台沙箱直接 ModuleNotFoundError（GUA-208 实盘 RE）。
        _py_names = [n for n in names if n.endswith(".py")]
        _pkg_dirs: set[str] = set()
        for _n in _py_names:
            _parts = _n.split("/")
            for _i in range(1, len(_parts)):
                _pkg_dirs.add("/".join(_parts[:_i]))
        _miss = sorted(_d for _d in _pkg_dirs if _d + "/__init__.py" not in names)
        if _miss:
            print(f"[失败] 包目录缺少 __init__.py（py3.6 zipimport 无法导入命名空间包）: {_miss}")
            return False
        # 语法校验 __main__.py
        code = zf.read("__main__.py").decode("utf-8")
        try:
            compile(code, "__main__.py", "exec")
        except SyntaxError as e:
            print(f"[失败] __main__.py 语法错误: {e}")
            return False
        # 全量 py3.6 语法编译校验（平台沙箱 = Ubuntu 16.04 / python3.6）：
        # 3.7+ 语法（walrus/match/f-string=）或损坏文件会导致上传"未知错误"。
        for n in names:
            if not n.endswith(".py"):
                continue
            try:
                _code = zf.read(n).decode("utf-8")
                compile(_code, n, "exec", ast.PyCF_ONLY_AST)
                # py3.6 编译级校验：PEP563 future import 在 py3.6 编译即崩，
                # 校验失败证明打包变换漏网（本机 3.12 的 compile 无法模拟 py3.6）。
                try:
                    ast.parse(_code, filename=n, feature_version=(3, 6))
                except SyntaxError as e:
                    print(f"[失败] {n} py3.6 语法不兼容: {e}")
                    return False
                # 兜底：显式确认 PEP563 future import 已被剥离（feature_version 检查捕不到）
                if re.search(r"(?m)^from __future__ import annotations", _code):
                    print(f"[失败] {n} 仍含 from __future__ import annotations（py3.6 编译崩）")
                    return False
            except Exception as e:
                print(f"[失败] {n} 无法编译: {e}")
                return False
        # 不应包含非决策链内容（上传会被平台拒绝/解析失败）
        for n in names:
            if "/train/" in n or n.startswith("train/") or ".backup" in n \
               or n.endswith(".md") or n.endswith(".txt"):
                print(f"[失败] zip 内含非决策链文件: {n}")
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
        # 补缺失 __init__.py：py3.6 zipimport 不认 PEP420 命名空间包，
        # 缺则 `import src` / `import src.communication` 在平台沙箱崩（GUA-208 实盘 RE）。
        _rel_set = {rel for _, rel in files}
        _pkg_dirs: set[str] = set()
        for _rel in _rel_set:
            _parts = _rel.split("/")
            for _i in range(1, len(_parts)):
                _pkg_dirs.add("/".join(_parts[:_i]))
        for _d in sorted(_pkg_dirs):
            if _d + "/__init__.py" not in _rel_set:
                zf.writestr(_d + "/__init__.py", "")
                print(f"[补] {_d}/__init__.py（py3.6 zipimport 命名空间包兼容）")
        for src, rel in files:
            if src.suffix == ".py":
                # 剥 BOM（平台后端解析 utf-8 遇 BOM 头可能失败 → 上传"未知错误"）
                # + py3.6 兼容变换（剥离 future import / 注解字符串化，GUA-203）
                try:
                    data = src.read_bytes()
                    if data[:3] == b"\xef\xbb\xbf":
                        data = data[3:]
                    text = data.decode("utf-8")
                    text = _py36_transform(text, rel)
                    zf.writestr(rel, text.encode("utf-8"))
                    continue
                except (OSError, UnicodeDecodeError) as e:
                    print(f"[警告] {rel} 跳过变换: {e}")
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
