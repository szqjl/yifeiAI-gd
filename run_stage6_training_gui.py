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

# 在导入torch之前尝试设置CUDA_VISIBLE_DEVICES，避免旧GPU警告
# 注意：警告可能仍然会出现，但训练时会使用正确的GPU
try:
    import subprocess
    # 尝试使用nvidia-smi检测GPU（如果可用）
    result = subprocess.run(['nvidia-smi', '--query-gpu=index,name,compute_cap', '--format=csv,noheader'], 
                          capture_output=True, text=True, timeout=3)
    if result.returncode == 0:
        lines = result.stdout.strip().split('\n')
        compatible_gpu_id = None
        for line in lines:
            parts = line.split(', ')
            if len(parts) >= 3:
                gpu_id = int(parts[0].strip())
                gpu_name = parts[1].strip()
                compute_cap = parts[2].strip()
                try:
                    major, minor = map(int, compute_cap.split('.'))
                    capability = major * 10 + minor
                    if capability >= 37:
                        if compatible_gpu_id is None:
                            compatible_gpu_id = gpu_id
                            print(f"✓ 找到兼容的GPU {gpu_id}: {gpu_name} (Capability {compute_cap})")
                        else:
                            print(f"  备用GPU {gpu_id}: {gpu_name} (Capability {compute_cap})")
                    else:
                        print(f"⚠ 跳过旧GPU {gpu_id}: {gpu_name} (Capability {compute_cap} < 3.7)")
                except:
                    pass
        
        if compatible_gpu_id is not None:
            os.environ['CUDA_VISIBLE_DEVICES'] = str(compatible_gpu_id)
            print(f"✓ 已设置CUDA_VISIBLE_DEVICES={compatible_gpu_id}，将只使用兼容的GPU")
except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
    # nvidia-smi不可用，将在导入torch后检测
    pass

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
