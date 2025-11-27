#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量游戏执行系统 - 主启动脚本

这是批量游戏执行系统的主入口点。
可以直接运行此脚本来启动批量执行器。

使用方法:
    python batch_executor.py --server-path <服务器路径> [选项]

示例:
    # 执行100场游戏（默认）
    python batch_executor.py --server-path guandan_offline_v1006.exe
    
    # 执行200场游戏
    python batch_executor.py --server-path guandan_offline_v1006.exe --target-games 200
    
    # 仅运行诊断
    python batch_executor.py --server-path guandan_offline_v1006.exe --diagnose-only
"""

import sys
import os

# 确保可以导入batch_executor模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入并运行主函数
from batch_executor.main import main

if __name__ == '__main__':
    main()
