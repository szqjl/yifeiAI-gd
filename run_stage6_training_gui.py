#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段6游戏导向训练GUI启动脚本
运行命令：python run_stage6_training_gui.py
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

try:
    # 优先使用增强版GUI，如果失败则回退到简化版
    try:
        from stage6_training_gui_enhanced import main as enhanced_main
        print("🎯 启动阶段6游戏导向训练GUI（增强版）...")
        print("✨ 功能包括：数据管理、格式转换、训练监控、评估等")
        enhanced_main()
    except ImportError:
        # 回退到简化版
        from stage6_training_gui_simple import main as simple_main
        print("🎯 启动阶段6游戏导向训练GUI（简化版）...")
        simple_main()

except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("请确保所有依赖都已安装")
    sys.exit(1)

except KeyboardInterrupt:
    print("\n👋 GUI已关闭")

except Exception as e:
    print(f"❌ 运行错误: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
