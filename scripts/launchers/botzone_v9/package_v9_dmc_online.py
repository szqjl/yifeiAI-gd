#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V9 轻量 DMC Botzone 在线 Bot 打包（方案 A）。

产出：data/eval/botzone/v9_dmc_online_bot_<日期>_v9_<N>.zip

结构：
  __main__.py
  external/FableDan/fabledan/   # 仿真编码子集
  src/communication/botzone_adapter.py
  src/v/nn/inference/
  src/v/nn/training/{dmc_mlp,fabledan_v8_bridge,fd_env}.py

权重不打入 zip → Botzone 用户存储 data/dmc_v9_weights.npz

用法：
  python scripts/launchers/botzone_v9/package_v9_dmc_online.py
  python scripts/launchers/botzone_v9/package_v9_dmc_online.py --dry-run
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import json
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ENTRY = _REPO_ROOT / "scripts" / "launchers" / "botzone_v9" / "__main__.py"
_OUT_DIR = _REPO_ROOT / "data" / "eval" / "botzone"

_INCLUDE_TOP = (
    "external/FableDan/fabledan",
    "src/v/nn/inference",
)
_INCLUDE_FILES = (
    "src/communication/botzone_adapter.py",
    "src/v/nn/training/dmc_mlp.py",
    "src/v/nn/training/fabledan_v8_bridge.py",
    "src/v/nn/training/fd_env.py",
    "src/v/nn/training/__init__.py",
    "src/v/__init__.py",
)

# V9 不含 V7 引擎；勿打包仓库版 src/v/nn/__init__.py（会 import ultimate_win_rate_engine_v7）
_V9_NN_INIT_STUB = (
    "# -*- coding: utf-8 -*-\n"
    '"""V9 Botzone 轻量包：不导入 V7 引擎。"""\n'
)

_FABLEDAN_SKIP = (
    "train_demo.py",
    "train_fast.py",
    "train.py",
    "model_torch.py",
    "model_np.py",
    "ring.py",
    "evaluate.py",
)

_EXCLUDE_SNIPPETS = (
    "__pycache__",
    "scripts",
    "data",
    "logs",
    "tests",
    ".git",
    "*.pyc",
    "*.pth",
    "*.pt",
    "*.npz",
    "*.zip",
    "*.log",
    "*.md",
)


def _version_slug(rev: int) -> str:
    today = datetime.now().strftime("%Y%m%d")
    return f"v9_dmc_online_bot_{today}_v9_{rev}.zip"


def _latest_rev() -> int:
    if not _OUT_DIR.exists():
        return 0
    best = 0
    for p in _OUT_DIR.iterdir():
        m = re.match(r"v9_dmc_online_bot_\d{8}_v9_(\d+)\.zip$", p.name)
        if m:
            best = max(best, int(m.group(1)))
    return best


def _should_skip(rel: str) -> bool:
    name = rel.rsplit("/", 1)[-1]
    if name in _FABLEDAN_SKIP:
        return True
    parts = rel.replace("\\", "/").split("/")
    if any(s in parts for s in ("__pycache__", "scripts", "tests", ".git")):
        return True
    return any(fnmatch.fnmatch(rel, s) or rel.endswith(s) for s in _EXCLUDE_SNIPPETS)


def _py36_transform(src: str, filename: str) -> str:
    src = re.sub(r"(?m)^from __future__ import annotations[ \t]*\r?\n", "", src)
    try:
        tree = ast.parse(src, filename=filename)
    except SyntaxError:
        return src
    line_starts = [0]
    for line in src.splitlines(True):
        line_starts.append(line_starts[-1] + len(line))

    def to_offsets(node):
        start = line_starts[node.lineno - 1] + node.col_offset
        end = line_starts[node.end_lineno - 1] + node.end_col_offset
        return start, end

    def expr_to_str(node):
        s, e = to_offsets(node)
        return src[s:e]

    spans = []

    def add_annotation(ann):
        if ann is None:
            return
        if isinstance(ann, ast.Constant) and isinstance(ann.value, str):
            return
        s, e = to_offsets(ann)
        spans.append((s, e, expr_to_str(ann)))

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            add_annotation(node.returns)
            for a in list(node.args.posonlyargs) + list(node.args.args) + list(node.args.kwonlyargs):
                add_annotation(a.annotation)
            if node.args.vararg:
                add_annotation(node.args.vararg.annotation)
            if node.args.kwarg:
                add_annotation(node.args.kwarg.annotation)
        elif isinstance(node, ast.AnnAssign):
            add_annotation(node.annotation)

    out = src
    for s, e, text in sorted(spans, key=lambda x: -x[0]):
        out = out[:s] + json.dumps(text, ensure_ascii=True) + out[e:]
    return out


def collect_files():
    files = []
    for top in _INCLUDE_TOP:
        top_dir = _REPO_ROOT / top
        if not top_dir.exists():
            print(f"[警告] 缺失: {top_dir}")
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
        if p.exists():
            files.append((p, rel))
        else:
            print(f"[警告] 缺失: {p}")
    files.append((_ENTRY, "__main__.py"))
    return files


def _validate_zip(path: Path) -> bool:
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
        if "__main__.py" not in names:
            print("[失败] 缺少 __main__.py")
            return False
        if not any(n.startswith("src/v/nn/inference/") for n in names):
            print("[失败] 缺少 src/v/nn/inference/")
            return False
        nn_init = zf.read("src/v/nn/__init__.py").decode("utf-8")
        if "ultimate_win_rate_engine_v7" in nn_init:
            print("[失败] src/v/nn/__init__.py 仍引用 V7 引擎")
            return False
        for n in names:
            if not n.endswith(".py"):
                continue
            body = zf.read(n).decode("utf-8", errors="replace")
            if "from src.v.nn.training.actor" in body or "import actor" in body:
                print(f"[失败] {n} 仍依赖 training.actor（V9 包未含）")
                return False
        _py_names = [n for n in names if n.endswith(".py")]
        _pkg_dirs = set()
        for _n in _py_names:
            _parts = _n.split("/")
            for _i in range(1, len(_parts)):
                _pkg_dirs.add("/".join(_parts[:_i]))
        _miss = sorted(_d for _d in _pkg_dirs if _d + "/__init__.py" not in names)
        if _miss:
            print(f"[失败] 缺少 __init__.py: {_miss}")
            return False
        for n in names:
            if not n.endswith(".py"):
                continue
            code = zf.read(n).decode("utf-8")
            compile(code, n, "exec", ast.PyCF_ONLY_AST)
            ast.parse(code, filename=n, feature_version=(3, 6))
    if not _validate_zip_import_smoke(path):
        return False
    size_mb = path.stat().st_size / 1024 / 1024
    print(f"[OK] zip 校验通过: {path.name} ({size_mb:.2f} MB)")
    return True


def _validate_zip_import_smoke(path: Path) -> bool:
    """解压后导入 DmcBotzoneDecider，捕获缺模块问题。"""
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        with zipfile.ZipFile(path) as zf:
            zf.extractall(td_path)
        code = (
            "from src.v.nn.inference.dmc_botzone_decide import DmcBotzoneDecider; "
            "DmcBotzoneDecider(); print('import_ok')"
        )
        proc = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(td_path),
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            print("[失败] zip 导入冒烟:")
            print((proc.stderr or proc.stdout)[-2000:])
            return False
    print("[OK] zip 导入冒烟通过")
    return True


def build(args) -> int:
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    if args.check:
        rev = _latest_rev()
        if rev == 0:
            print("[提示] 无 v9 zip")
            return 0
        return 0 if _validate_zip(_OUT_DIR / _version_slug(rev)) else 1

    files = collect_files()
    print(f"[收集] {len(files)} 个文件")
    if args.dry_run:
        for _, rel in files:
            print("  " + rel)
        return 0

    rev = args.rev or (_latest_rev() + 1)
    out_path = _OUT_DIR / _version_slug(rev)
    rel_set = {rel for _, rel in files}
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        pkg_dirs = set()
        for rel in rel_set:
            parts = rel.split("/")
            for i in range(1, len(parts)):
                pkg_dirs.add("/".join(parts[:i]))
        for d in sorted(pkg_dirs):
            if d == "src/v/nn":
                continue
            if d + "/__init__.py" not in rel_set:
                zf.writestr(d + "/__init__.py", "")
        zf.writestr("src/v/nn/__init__.py", _V9_NN_INIT_STUB)
        for src, rel in files:
            if src.suffix == ".py":
                data = src.read_bytes()
                if data[:3] == b"\xef\xbb\xbf":
                    data = data[3:]
                text = _py36_transform(data.decode("utf-8"), rel)
                zf.writestr(rel, text.encode("utf-8"))
            else:
                zf.write(src, rel)
    print(f"[产出] {out_path}")
    return 0 if _validate_zip(out_path) else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="V9 DMC Botzone 在线 Bot 打包")
    parser.add_argument("--rev", type=int, default=0)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    return build(args)


if __name__ == "__main__":
    sys.exit(main())
