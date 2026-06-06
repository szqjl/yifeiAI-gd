#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""将 lalala 核心模块复制到 reference/lalala（ASCII 路径，供 V7 批跑使用）。"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.utils.v7_paths import get_lalala_dir, sync_lalala_to_reference


def main() -> int:
    dest = sync_lalala_to_reference(REPO_ROOT)
    print(f"已同步 lalala → {dest}")
    print(f"当前 get_lalala_dir() = {get_lalala_dir(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
