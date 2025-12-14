#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略学习任务训练脚本（6个策略任务）
重点学习：
1. 如何组牌
2. 如何判断牌力，并决定自身是主攻还是助攻角色
3. 根据角色来定位，如何保护队友、如何压制对手
4. 炸弹出炸时机
5. 红心配如何更好的组牌、发挥作用
6. 根据角色来定位，首发牌怎么出、开局怎么打、中期怎么出、残局怎么判断
"""

import sys
import os
import random
import torch
import numpy as np
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.train.pretrain import train_bc

# 强制使用CPU训练（避免GPU内存问题）
os.environ['FORCE_CPU'] = '1'

# 固定随机种子
seed = 42
random.seed(seed)
np.random.seed(seed)
torch.manual_seed(seed)

print("="*80)
print("策略学习任务训练 - 6个策略任务")
print("="*80)
print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"随机种子: {seed}")
print(f"使用设备: CPU")
print("="*80)
print()

print("[6个策略学习任务]")
print("1. 组牌策略分类（7类：不组牌/组对子/组三张/组三带二/组顺子/组钢板/组木板）")
print("2. 角色判断（3类：主攻/助攻/平衡）")
print("3. 牌力评估（回归：0-10分）")
print("4. 保护/压制判断（3类：保护队友/压制对手/无）")
print("5. 炸弹出炸时机（5类：开局/中期/残局/关键压制/不出）")
print("6. 红心配策略（4类：组牌/炸弹/保留/不使用）")
print()

print("[训练配置]")
print("1. 动作预测权重: 1.5 (主任务)")
print("2. 策略分类权重: 0.3 (辅助任务)")
print("3. 策略任务权重: 0.5 (6个任务总权重，平均每个约0.083)")
print("4. **新增** 策略一致性损失权重: 0.2-0.5 (鼓励动作和策略同时正确)")
print("5. 数据量: 10000样本（可根据需要调整）")
print("6. 训练轮数: 50 epochs")
print("7. 批次大小: 64")
print("8. 学习率: 0.0003")
print("9. Dropout: 0.1")
print()
print("[改进措施]")
print("1. **策略一致性损失**: 如果动作预测基本正确（卡牌匹配率>90%），策略分类也应该正确")
print("2. **联合损失**: 使用卡牌匹配率作为权重，鼓励动作和策略同时正确")
print("3. **改进的策略理解率**: 使用90%匹配率标准（而不是100%完全匹配）")
print("   这样更符合实际：卡牌级别准确率97.38%，90%匹配率更合理")
print()

print("[监控信息]")
print("- 每个epoch结束后显示：")
print("  * 总损失、动作损失、策略损失、策略任务损失")
print("  * 完全匹配准确率、卡牌级别准确率")
print("  * 策略分类准确率、策略理解率")
print("  * 6个策略任务的准确率（如果可计算）")
print("- 每10个epoch保存检查点")
print("- 训练完成后保存最终模型")
print()

# 创建模型保存目录
model_dir = "models"
os.makedirs(model_dir, exist_ok=True)

# 创建训练日志目录
log_dir = "training_logs"
os.makedirs(log_dir, exist_ok=True)

# 训练日志文件
log_file = os.path.join(log_dir, f"strategy_tasks_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

print(f"[日志文件] {log_file}")
print()

# 开始训练
try:
    train_bc(
        data_dir="game_records",
        epochs=50,                    # 训练轮数
        batch_size=64,                # 批次大小
        lr=0.0003,                    # 学习率
        dropout_rate=0.1,             # Dropout比率
        model_path="models/bc_model_strategy_tasks.pth",  # 模型保存路径
        max_samples=10000,            # 使用10000个样本（可根据需要调整）
        enable_strategy_head=True,     # 启用策略分类头
        action_loss_weight=1.5,       # 动作预测权重
        strategy_loss_weight=0.3,      # 策略分类权重
        use_improved_model=True,      # 使用改进的模型（包含注意力机制）
        attention_heads=8,             # 注意力头数
        # 阶段5任务（可选，暂时禁用以专注于6个策略任务）
        enable_strategy_pattern=False,
        strategy_pattern_weight=0.0,
        enable_opponent_modeling=False,
        opponent_model_weight=0.0,
        enable_dynamic_strategy=False,
        dynamic_strategy_weight=0.0
    )
    
    print()
    print("="*80)
    print("策略学习任务训练完成")
    print("="*80)
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"模型保存路径: models/bc_model_strategy_tasks.pth")
    print("="*80)
    
except KeyboardInterrupt:
    print()
    print("="*80)
    print("训练被用户中断")
    print("="*80)
    print("提示：训练进度已保存，可以继续训练")
    
except Exception as e:
    print()
    print("="*80)
    print(f"训练过程中发生错误: {e}")
    print("="*80)
    import traceback
    traceback.print_exc()

