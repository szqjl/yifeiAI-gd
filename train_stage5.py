#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段5模型训练脚本
训练包含策略模式识别、对手建模、动态策略调整的完整模型
"""

import sys
import os
import random
import torch
import numpy as np

# 添加项目路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.train.pretrain import train_bc

# **修复**: 检查GPU兼容性，选择兼容的GPU或使用CPU
# 如果检测到旧GPU（CUDA capability < 3.7），尝试使用兼容的GPU或切换到CPU
use_cpu = False
compatible_gpu_id = None

if torch.cuda.is_available():
    try:
        # 尝试获取GPU的CUDA capability，找到第一个兼容的GPU
        device_count = torch.cuda.device_count()
        for i in range(device_count):
            props = torch.cuda.get_device_properties(i)
            capability = props.major * 10 + props.minor
            if capability < 37:  # CUDA capability < 3.7
                print(f"[警告] 检测到旧GPU: {props.name} (CUDA capability {props.major}.{props.minor})")
                print(f"[警告] PyTorch不再支持此GPU，将跳过")
            else:
                if compatible_gpu_id is None:
                    compatible_gpu_id = i
                    print(f"[信息] 找到兼容GPU: {props.name} (CUDA capability {props.major}.{props.minor})")
        
        # 如果没有找到兼容的GPU，使用CPU
        if compatible_gpu_id is None:
            print(f"[警告] 未找到兼容的GPU，将使用CPU训练")
            use_cpu = True
        else:
            # 设置使用指定的GPU
            os.environ['CUDA_VISIBLE_DEVICES'] = str(compatible_gpu_id)
            print(f"[信息] 将使用GPU {compatible_gpu_id}: {torch.cuda.get_device_name(compatible_gpu_id)}")
    except Exception as e:
        print(f"[警告] 无法检测GPU信息: {e}")
        print(f"[警告] 将使用CPU训练以避免兼容性问题")
        use_cpu = True

# 如果用户明确指定使用CPU，则使用CPU
if os.environ.get('FORCE_CPU', '0') == '1':
    use_cpu = True
    compatible_gpu_id = None

# 设置环境变量以强制使用CPU（如果需要）
if use_cpu:
    os.environ['FORCE_CPU'] = '1'
    # 清除CUDA_VISIBLE_DEVICES，确保使用CPU
    if 'CUDA_VISIBLE_DEVICES' in os.environ:
        del os.environ['CUDA_VISIBLE_DEVICES']

# 固定随机种子，确保训练可复现
seed = 42
random.seed(seed)
np.random.seed(seed)
torch.manual_seed(seed)
if torch.cuda.is_available() and not use_cpu:
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

print("="*80)
print("阶段5模型训练 - 完整训练")
print("="*80)
print(f"训练时间: {np.datetime64('now')}")
print(f"随机种子: {seed}")
print(f"CUDA可用: {torch.cuda.is_available()}")
if torch.cuda.is_available() and not use_cpu:
    print(f"CUDA设备: {torch.cuda.get_device_name(0)}")
elif use_cpu:
    print(f"使用设备: CPU（GPU不可用或太旧）")
else:
    print(f"使用设备: CPU（CUDA不可用）")
print("="*80)
print()

# 阶段5模型训练配置
# **注意**: GTX 1650的4GB显存不足以运行阶段5完整模型，建议使用CPU训练
# 如果GPU内存不足，会自动切换到CPU训练
print("[信息] 阶段5模型包含多个组件，需要较大内存")
print("[信息] 如果GPU内存不足，建议使用CPU训练（设置 FORCE_CPU=1）")
print()

# 阶段5模型训练配置
# 根据数据量（约50,000+样本），使用50 epochs
train_bc(
    data_dir="game_records",
    epochs=50,                    # 大数据量用50
    batch_size=32 if not use_cpu else 64,  # CPU训练可以使用更大的batch_size
    lr=0.0003,
    dropout_rate=0.1,
    model_path="models/bc_model_stage5_final.pth",
    enable_strategy_head=True,
    action_loss_weight=1.5,
    strategy_loss_weight=0.3,
    use_improved_model=True,
    attention_heads=8,
    enable_strategy_pattern=True,
    strategy_pattern_weight=0.2,
    enable_opponent_modeling=True,
    opponent_model_weight=0.15,
    enable_dynamic_strategy=True,
    dynamic_strategy_weight=0.1
)

print()
print("="*80)
print("阶段5模型训练完成")
print("="*80)

