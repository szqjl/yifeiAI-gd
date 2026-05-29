# -*- coding: utf-8 -*-
"""Phase 5g: archive docs/implementation/ (legacy V6 implementation guides)."""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DIR_STUB = """# 目录已迁移

> **新位置**：[{target}]({target})  
> **归类说明**：[DOCUMENT_AUDIT.md](../governance/DOCUMENT_AUDIT.md)（Phase 5g）

历史 V6 实施指导；日常开发见 `development/`、`guandan-brain/`。请勿在本路径继续编辑。
"""


def main() -> None:
    src = ROOT / "docs/implementation"
    dst = ROOT / "docs/archive/implementation"
    if src.is_dir() and not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        print("OK", src.relative_to(ROOT), "->", dst.relative_to(ROOT))
    elif dst.exists():
        print("exists", dst)
    else:
        print("skip missing", src)

    stub_dir = ROOT / "docs/implementation"
    stub_dir.mkdir(parents=True, exist_ok=True)
    (stub_dir / "README.md").write_text(
        DIR_STUB.format(target="archive/implementation/"), encoding="utf-8"
    )
    print("stub docs/implementation/README.md")
    print("done")


if __name__ == "__main__":
    main()
