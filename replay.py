#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
游戏回放工具 - 纯Python版本（避免编码问题）
"""

import sys
import os
from pathlib import Path

# 设置路径
script_dir = Path(__file__).parent.absolute()
src_dir = script_dir / "src"
sys.path.insert(0, str(src_dir))
os.environ['PYTHONPATH'] = str(src_dir)

# 导入回放模块
try:
    from communication.replay_select import select_and_replay
except ImportError as e:
    print(f"导入错误: {e}")
    print(f"请确保在项目根目录运行此脚本")
    sys.exit(1)


def main():
    """主函数"""
    print("=" * 60)
    print("游戏回放工具")
    print("=" * 60)
    print()
    
    # 选择模式
    print("选择回放模式:")
    print("  [1] 基础回放模式 - 快速查看完整回放")
    print("  [2] 交互式回放模式 - 支持上一步/下一步/自动播放（推荐）")
    print("  [3] 退出")
    print()
    
    try:
        mode = input("请选择模式 (1-3): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n已取消")
        return
    
    if mode == "3":
        return
    
    if mode not in ["1", "2"]:
        print("无效的选择")
        return
    
    print()
    print("=" * 60)
    print("正在加载游戏记录列表...")
    print("=" * 60)
    print()
    
    # 执行回放
    try:
        select_and_replay(interactive=(mode == "2"))
    except KeyboardInterrupt:
        print("\n\n已取消")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

