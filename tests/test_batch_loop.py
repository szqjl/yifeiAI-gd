#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试batch_executor循环逻辑
"""

import os
import sys
from pathlib import Path

# 添加项目路径
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

def test_loop_logic():
    """测试循环逻辑"""

    # 模拟状态
    target_games = 50
    completed_games = 0
    running = True
    batch_count = 0

    print(f"目标游戏数: {target_games}")
    print(f"单批次限制: 3")

    while completed_games < target_games and running:
        batch_count += 1
        batch_games = min(3, target_games - completed_games)  # 模拟batch_games计算

        print(f"\n批次 {batch_count}:")
        print(f"  本批次游戏数: {batch_games}")
        print(f"  执行前已完成: {completed_games}")

        # 模拟执行一批次
        print(f"  模拟执行 {batch_games} 场游戏...")

        # 模拟完成一批次
        completed_games += batch_games
        print(f"  执行后已完成: {completed_games}")

        # 检查是否需要继续
        if completed_games < target_games:
            print(f"  {completed_games} < {target_games}，需要继续下一批次")
        else:
            print(f"  {completed_games} >= {target_games}，所有游戏完成")
            break

    print(f"\n循环结束:")
    print(f"  总批次数: {batch_count}")
    print(f"  最终完成游戏数: {completed_games}")
    print(f"  目标游戏数: {target_games}")

if __name__ == '__main__':
    test_loop_logic()