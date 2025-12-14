#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析策略学习任务训练效果
"""

import json
import os
from pathlib import Path
from datetime import datetime

def analyze_training_effect():
    """分析训练效果"""
    print("="*80)
    print("策略学习任务训练效果分析")
    print("="*80)
    print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. 读取训练历史
    history_path = Path("models/bc_model_strategy_tasks_training_history.json")
    if not history_path.exists():
        print("❌ 训练历史文件不存在")
        return
    
    with open(history_path, 'r', encoding='utf-8') as f:
        history = json.load(f)
    
    epochs = history.get('epochs', [])
    if not epochs:
        print("❌ 训练历史为空")
        return
    
    print(f"✓ 训练完成: {max(epochs)}/50 epochs")
    print()
    
    # 2. 分析主要指标趋势
    print("[主要指标趋势]")
    print("-"*80)
    
    # 总损失
    total_losses = history.get('total_loss', [])
    if total_losses:
        initial_loss = total_losses[0] if len(total_losses) > 0 else 0
        final_loss = total_losses[-1] if len(total_losses) > 0 else 0
        print(f"总损失: {initial_loss:.4f} → {final_loss:.4f} (降低 {initial_loss - final_loss:.4f})")
    
    # 动作损失
    action_losses = history.get('action_loss', [])
    if action_losses:
        initial_action = action_losses[0] if len(action_losses) > 0 else 0
        final_action = action_losses[-1] if len(action_losses) > 0 else 0
        print(f"动作损失: {initial_action:.4f} → {final_action:.4f} (降低 {initial_action - final_action:.4f})")
    
    # 策略损失
    strategy_losses = history.get('strategy_loss', [])
    if strategy_losses:
        initial_strategy = strategy_losses[0] if len(strategy_losses) > 0 else 0
        final_strategy = strategy_losses[-1] if len(strategy_losses) > 0 else 0
        print(f"策略损失: {initial_strategy:.4f} → {final_strategy:.4f} (降低 {initial_strategy - final_strategy:.4f})")
    
    print()
    
    # 3. 分析准确率
    print("[准确率指标]")
    print("-"*80)
    
    # 完全匹配准确率
    exact_accuracies = history.get('action_exact_accuracy', [])
    if exact_accuracies:
        final_exact = exact_accuracies[-1] if len(exact_accuracies) > 0 else 0
        max_exact = max(exact_accuracies) if exact_accuracies else 0
        print(f"完全匹配准确率: {final_exact:.2%} (最高: {max_exact:.2%})")
    
    # 卡牌级别准确率
    card_accuracies = history.get('action_card_accuracy', [])
    if card_accuracies:
        final_card = card_accuracies[-1] if len(card_accuracies) > 0 else 0
        max_card = max(card_accuracies) if card_accuracies else 0
        print(f"卡牌级别准确率: {final_card:.2%} (最高: {max_card:.2%})")
    
    # 策略分类准确率
    strategy_accuracies = history.get('strategy_accuracy', [])
    if strategy_accuracies:
        final_strategy_acc = strategy_accuracies[-1] if len(strategy_accuracies) > 0 else 0
        max_strategy_acc = max(strategy_accuracies) if strategy_accuracies else 0
        print(f"策略分类准确率: {final_strategy_acc:.2%} (最高: {max_strategy_acc:.2%})")
    
    # 策略理解率
    understanding_rates = history.get('strategy_understanding_rate', [])
    if understanding_rates:
        final_understanding = understanding_rates[-1] if len(understanding_rates) > 0 else 0
        max_understanding = max(understanding_rates) if understanding_rates else 0
        print(f"策略理解率: {final_understanding:.2%} (最高: {max_understanding:.2%})")
    
    print()
    
    # 4. 分析各epoch的关键指标
    print("[关键epoch指标]")
    print("-"*80)
    key_epochs = [1, 10, 20, 30, 40, 50]
    for epoch in key_epochs:
        if epoch in epochs:
            idx = epochs.index(epoch)
            print(f"\nEpoch {epoch}:")
            if idx < len(total_losses):
                print(f"  总损失: {total_losses[idx]:.4f}")
            if idx < len(action_losses):
                print(f"  动作损失: {action_losses[idx]:.4f}")
            if idx < len(exact_accuracies):
                print(f"  完全匹配: {exact_accuracies[idx]:.2%}")
            if idx < len(card_accuracies):
                print(f"  卡牌准确率: {card_accuracies[idx]:.2%}")
            if idx < len(strategy_accuracies):
                print(f"  策略准确率: {strategy_accuracies[idx]:.2%}")
    
    print()
    
    # 5. 分析6个策略任务的效果（如果训练历史中有记录）
    print("[6个策略任务效果]")
    print("-"*80)
    print("注意: 策略任务的具体准确率需要在训练代码中添加记录")
    print("当前训练历史中主要记录了:")
    print("  - 动作预测准确率")
    print("  - 策略分类准确率（7类策略）")
    print("  - 策略理解率（动作+策略都正确）")
    print()
    print("6个策略任务的学习效果体现在:")
    print("  1. 组牌策略 - 通过动作预测准确率间接体现")
    print("  2. 角色判断 - 通过策略分类准确率间接体现")
    print("  3. 牌力评估 - 通过损失函数优化体现")
    print("  4. 保护/压制 - 通过策略分类准确率间接体现")
    print("  5. 炸弹出炸时机 - 通过策略分类准确率间接体现")
    print("  6. 红心配策略 - 通过动作预测准确率间接体现")
    
    print()
    print("="*80)
    print("训练效果总结")
    print("="*80)
    
    # 总结
    if exact_accuracies and card_accuracies:
        print(f"✓ 训练已完成 {max(epochs)} 个epochs")
        print(f"✓ 卡牌级别准确率: {card_accuracies[-1]:.2%} (表现良好)")
        if strategy_accuracies:
            print(f"✓ 策略分类准确率: {strategy_accuracies[-1]:.2%} (表现{'优秀' if strategy_accuracies[-1] > 0.9 else '良好' if strategy_accuracies[-1] > 0.7 else '一般'})")
        if understanding_rates:
            print(f"✓ 策略理解率: {understanding_rates[-1]:.2%} (动作和策略都正确)")
        
        print()
        print("建议:")
        if exact_accuracies[-1] < 0.05:
            print("  - 完全匹配准确率较低，可能需要:")
            print("    * 增加训练数据量")
            print("    * 调整损失函数权重")
            print("    * 优化模型架构")
        if card_accuracies[-1] > 0.95:
            print("  - 卡牌级别准确率很高，说明模型能正确识别卡牌")
        if strategy_accuracies and strategy_accuracies[-1] > 0.9:
            print("  - 策略分类准确率很高，说明模型理解了策略类型")
    
    print("="*80)

if __name__ == "__main__":
    analyze_training_effect()

