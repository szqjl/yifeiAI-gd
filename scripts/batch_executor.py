#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量游戏执行系统 - 主启动脚本

这是批量游戏执行系统的主入口点。
可以直接运行此脚本来启动批量执行器。

使用方法:
    python scripts/batch_executor.py --server-path <服务器路径> [选项]

示例:
    # 执行100场游戏（默认）
    python scripts/batch_executor.py --server-path guandan_offline_v1006.exe

    # 执行200场游戏
    python scripts/batch_executor.py --server-path guandan_offline_v1006.exe --target-games 200

    # 仅运行诊断
    python scripts/batch_executor.py --server-path guandan_offline_v1006.exe --diagnose-only
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from batch_executor.main import main

if __name__ == '__main__':
    main()
