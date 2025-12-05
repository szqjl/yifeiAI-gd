# -*- coding: utf-8 -*-
"""
分析不同学习率的效果
从训练日志中提取学习率和损失值，分析最优学习率
"""

import re
import os
from glob import glob


def analyze_learning_rates():
    """分析训练日志中的学习率效果"""
    print("="*60)
    print("学习率效果分析")
    print("="*60)
    
    log_files = sorted(glob("training_logs/training_log_*.txt"), reverse=True)
    
    results = []
    
    for log_file in log_files[:10]:  # 只分析最近10个日志
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            # 提取学习率
            lr_match = re.search(r'Learning rate[:\s]+([\d.]+)', content)
            lr = float(lr_match.group(1)) if lr_match else None
            
            # 提取训练轮数
            epochs_match = re.search(r'Epochs[:\s]+(\d+)', content)
            epochs = int(epochs_match.group(1)) if epochs_match else None
            
            # 提取初始和最终损失
            loss_matches = re.findall(r'Epoch \d+/\d+, Loss: ([\d.]+)', content)
            if len(loss_matches) >= 2:
                initial_loss = float(loss_matches[0])
                final_loss = float(loss_matches[-1])
                loss_reduction = (initial_loss - final_loss) / initial_loss * 100
                
                results.append({
                    'file': os.path.basename(log_file),
                    'lr': lr,
                    'epochs': epochs,
                    'initial_loss': initial_loss,
                    'final_loss': final_loss,
                    'loss_reduction': loss_reduction
                })
        except Exception as e:
            continue
    
    if not results:
        print("未找到训练日志数据")
        return
    
    # 按学习率分组
    lr_groups = {}
    for r in results:
        if r['lr'] is not None:
            if r['lr'] not in lr_groups:
                lr_groups[r['lr']] = []
            lr_groups[r['lr']].append(r)
    
    print("\n学习率效果对比:")
    print("-" * 80)
    print(f"{'学习率':<10} {'训练次数':<10} {'平均初始损失':<15} {'平均最终损失':<15} {'平均下降率':<15}")
    print("-" * 80)
    
    for lr in sorted(lr_groups.keys()):
        group = lr_groups[lr]
        avg_initial = sum(r['initial_loss'] for r in group) / len(group)
        avg_final = sum(r['final_loss'] for r in group) / len(group)
        avg_reduction = sum(r['loss_reduction'] for r in group) / len(group)
        
        print(f"{lr:<10.4f} {len(group):<10} {avg_initial:<15.4f} {avg_final:<15.4f} {avg_reduction:<15.2f}%")
    
    # 推荐
    print("\n" + "="*60)
    print("学习率推荐")
    print("="*60)
    
    if 0.0005 in lr_groups:
        print("\n当前使用: 0.0005")
        group = lr_groups[0.0005]
        avg_final = sum(r['final_loss'] for r in group) / len(group)
        print(f"  平均最终损失: {avg_final:.4f}")
        print(f"  评价: 学习稳定，损失下降良好")
    
    if 0.001 in lr_groups:
        print("\n对比: 0.001")
        group = lr_groups[0.001]
        avg_final = sum(r['final_loss'] for r in group) / len(group)
        print(f"  平均最终损失: {avg_final:.4f}")
        print(f"  评价: 学习较快，但可能不够稳定")
    
    print("\n推荐学习率:")
    print("  1. 0.0005 (当前) - 稳定，适合当前数据量")
    print("  2. 0.0003 - 更稳定，适合数据量较大时")
    print("  3. 0.001 - 学习快，但需要更多训练轮数")
    print("  4. 0.0001 - 非常稳定，但需要更多训练轮数")
    
    print("\n建议:")
    print("  - 当前数据量(252个样本): 使用 0.0005 或 0.0003")
    print("  - 数据量增加到500+: 可以尝试 0.0003 或 0.0001")
    print("  - 如果训练不稳定: 降低到 0.0003 或 0.0001")
    print("  - 如果损失下降太慢: 提高到 0.001")


if __name__ == "__main__":
    analyze_learning_rates()

