# -*- coding: utf-8 -*-
"""Phase 5f: archive docs/rules, docs/skill; move claude-analysis; relocate lalala_src."""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DIR_STUB = """# 目录已迁移

> **新位置**：[{target}]({target})  
> **归类说明**：[DOCUMENT_AUDIT.md](../governance/DOCUMENT_AUDIT.md)（Phase 5f）

请勿在本路径继续新增或编辑；请打开上方链接。
"""


def move_tree(src: Path, dst: Path) -> None:
    if not src.exists():
        print("skip missing", src)
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        print("exists", dst)
        return
    shutil.move(str(src), str(dst))
    print("OK", src.relative_to(ROOT), "->", dst.relative_to(ROOT))


def write_stub(dir_path: Path, target_rel: str) -> None:
    dir_path.mkdir(parents=True, exist_ok=True)
    (dir_path / "README.md").write_text(
        DIR_STUB.format(target=target_rel), encoding="utf-8"
    )
    print("stub", dir_path.relative_to(ROOT))


def main() -> None:
    # rules / skill → archive
    move_tree(ROOT / "docs/rules", ROOT / "docs/archive/rules")
    write_stub(ROOT / "docs/rules", "archive/rules/")

    move_tree(ROOT / "docs/skill", ROOT / "docs/archive/skill")
    write_stub(ROOT / "docs/skill", "archive/skill/")

    # claude-analysis → analysis/agent-sessions
    move_tree(ROOT / "docs/claude-analysis", ROOT / "docs/analysis/agent-sessions")
    write_stub(ROOT / "docs/claude-analysis", "analysis/agent-sessions/")

    # lalala *.py → reference/lalala
    src_dir = ROOT / "docs/competition/lalala/lalala_src"
    ref_dir = ROOT / "reference/lalala"
    ref_dir.mkdir(parents=True, exist_ok=True)
    if src_dir.is_dir():
        for py in sorted(src_dir.glob("*.py")):
            dest = ref_dir / py.name
            if dest.exists():
                print("exists", dest)
                continue
            shutil.move(str(py), str(dest))
            print("OK", py.name, "-> reference/lalala/")
        idea = src_dir / ".idea"
        if idea.is_dir():
            shutil.rmtree(idea)
            print("removed", idea.relative_to(ROOT))
        write_stub(
            src_dir,
            "../../../reference/lalala/",
        )
        readme = src_dir / "README.md"
        readme.write_text(
            readme.read_text(encoding="utf-8")
            + "\n\n**分析文档**：`docs/competition/一等奖代码优秀特点分析.md`；"
            "`docs/guandan-brain/reviews/M1_vs_lalala_*.md`。\n",
            encoding="utf-8",
        )

    ref_readme = ref_dir / "README.md"
    if not ref_readme.exists():
        ref_readme.write_text(
            """# lalala 一等奖参考源码（东南大学）

> Phase 5f 自 `docs/competition/lalala/lalala_src/` 迁出；**勿在 `docs/` 内保留可 import 的 `.py`**。

## 用途

- 对照 M1/M2 决策与 lalala `action.py` / `utils.py`
- 批跑客户端：`src/communication/run_lalala_client3.py`、`run_lalala_client4.py`（非本目录直接 import）

## 相关文档

- [一等奖代码优秀特点分析](../../docs/competition/一等奖代码优秀特点分析.md)
- [M1 vs lalala 技法对照](../../docs/guandan-brain/reviews/M1_vs_lalala_TECHNIQUE_cursor.md)
""",
            encoding="utf-8",
        )

    print("done")


if __name__ == "__main__":
    main()
