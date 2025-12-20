#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速检查训练进度
"""

import os
import json
from pathlib import Path
from datetime import datetime

def check_training_progress():
    """检查训练进度"""
    print("="*80)
    print("训练进度检查")
    print("="*80)
    print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. 检查模型文件
    model_path = Path("models/bc_model_strategy_tasks.pth")
    if model_path.exists():
        size_mb = model_path.stat().st_size / (1024 * 1024)
        mtime = datetime.fromtimestamp(model_path.stat().st_mtime)
        print(f"✓ 最终模型: {model_path.name}")
        print(f"  大小: {size_mb:.2f} MB")
        print(f"  修改时间: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("✗ 最终模型: 尚未生成")
    
    print()
    
    # 2. 检查检查点文件
    checkpoints = sorted(Path("models").glob("bc_model_strategy_tasks_epoch_*.pth"))
    if checkpoints:
        print(f"✓ 检查点文件: {len(checkpoints)} 个")
        latest = checkpoints[-1]
        size_mb = latest.stat().st_size / (1024 * 1024)
        mtime = datetime.fromtimestamp(latest.stat().st_mtime)
        print(f"  最新: {latest.name}")
        print(f"  大小: {size_mb:.2f} MB")
        print(f"  修改时间: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 提取epoch编号
        try:
            epoch_num = int(latest.stem.split('_')[-1])
            print(f"  当前进度: {epoch_num}/50 epochs ({epoch_num*2}%)")
        except:
            pass
    else:
        print("✗ 检查点文件: 尚未生成")
    
    print()
    
    # 3. 检查训练历史
    history_path = Path("models/bc_model_strategy_tasks_training_history.json")
    if history_path.exists():
        print(f"✓ 训练历史: {history_path.name}")
        try:
            with open(history_path, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            epochs = history.get('epochs', [])
            if epochs:
                latest_epoch = max(epochs)
                print(f"  最新epoch: {latest_epoch}")
                
                # 显示最新epoch的指标
                idx = epochs.index(latest_epoch)
                print(f"  总损失: {history.get('total_loss', [])[idx]:.4f}" if idx < len(history.get('total_loss', [])) else "  N/A")
                print(f"  动作损失: {history.get('action_loss', [])[idx]:.4f}" if idx < len(history.get('action_loss', [])) else "  N/A")
                print(f"  策略损失: {history.get('strategy_loss', [])[idx]:.4f}" if idx < len(history.get('strategy_loss', [])) else "  N/A")
                print(f"  完全匹配准确率: {history.get('action_exact_accuracy', [])[idx]:.2%}" if idx < len(history.get('action_exact_accuracy', [])) else "  N/A")
                print(f"  卡牌级别准确率: {history.get('action_card_accuracy', [])[idx]:.2%}" if idx < len(history.get('action_card_accuracy', [])) else "  N/A")
                print(f"  策略分类准确率: {history.get('strategy_accuracy', [])[idx]:.2%}" if idx < len(history.get('strategy_accuracy', [])) else "  N/A")
        except Exception as e:
            print(f"  读取失败: {e}")
    else:
        print("✗ 训练历史: 尚未生成")
    
    print()
    
    # 4. 检查日志文件
    log_dir = Path("training_logs")
    if log_dir.exists():
        log_files = sorted(log_dir.glob("strategy_tasks_training_*.log"), key=lambda f: f.stat().st_mtime, reverse=True)
        if log_files:
            latest_log = log_files[0]
            size_kb = latest_log.stat().st_size / 1024
            mtime = datetime.fromtimestamp(latest_log.stat().st_mtime)
            print(f"✓ 训练日志: {latest_log.name}")
            print(f"  大小: {size_kb:.2f} KB")
            print(f"  修改时间: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 显示最后几行
            try:
                with open(latest_log, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    if lines:
                        print(f"\n[最新日志] (最后5行)")
                        for line in lines[-5:]:
                            print(f"  {line.rstrip()}")
            except:
                pass
        else:
            print("✗ 训练日志: 未找到")
    else:
        print("✗ 训练日志目录: 不存在")
    
    print()
    print("="*80)
    print("提示: 运行 'python train_strategy_tasks.py' 开始训练")
    print("     或运行 'START_STRATEGY_TASKS_TRAINING.bat' 启动训练")
    print("="*80)

if __name__ == "__main__":
    check_training_progress()

