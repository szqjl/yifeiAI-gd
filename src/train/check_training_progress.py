# -*- coding: utf-8 -*-
"""
定期检查方案F训练进度
"""

import sys
import os
import glob
import re
from datetime import datetime

# 修复Windows控制台编码
if sys.platform == 'win32':
    try:
        import io
        if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        if not isinstance(sys.stderr, io.TextIOWrapper) or sys.stderr.encoding != 'utf-8':
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

def find_latest_training_log():
    """找到最新的训练日志文件"""
    log_files = glob.glob("training_logs/solution_f_training_*.log")
    if not log_files:
        return None
    return max(log_files, key=os.path.getmtime)

def parse_training_progress(log_file):
    """解析训练进度"""
    if not os.path.exists(log_file):
        return None
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            if not lines:
                return None
            
            # 找到最后一个epoch的信息
            last_epoch_line = None
            for line in reversed(lines):
                if re.search(r'Epoch \d+/\d+', line):
                    last_epoch_line = line.strip()
                    break
            
            if not last_epoch_line:
                return None
            
            # 解析epoch信息
            epoch_match = re.search(r'Epoch (\d+)/(\d+)', last_epoch_line)
            if not epoch_match:
                return None
            
            current_epoch = int(epoch_match.group(1))
            total_epochs = int(epoch_match.group(2))
            
            # 解析loss和准确率
            loss_match = re.search(r'Loss: ([\d.]+)', last_epoch_line)
            exact_acc_match = re.search(r'Action Exact Accuracy: ([\d.]+)%', last_epoch_line)
            card_acc_match = re.search(r'Action Card Accuracy: ([\d.]+)%', last_epoch_line)
            lr_match = re.search(r'LR: ([\d.]+)', last_epoch_line)
            
            progress = {
                'current_epoch': current_epoch,
                'total_epochs': total_epochs,
                'progress_percent': (current_epoch / total_epochs) * 100,
                'loss': float(loss_match.group(1)) if loss_match else None,
                'exact_accuracy': float(exact_acc_match.group(1)) if exact_acc_match else None,
                'card_accuracy': float(card_acc_match.group(1)) if card_acc_match else None,
                'learning_rate': float(lr_match.group(1)) if lr_match else None,
                'last_line': last_epoch_line
            }
            
            # 检查是否完成
            if 'Training completed' in ''.join(lines[-10:]) or current_epoch >= total_epochs:
                progress['completed'] = True
            else:
                progress['completed'] = False
            
            return progress
    except Exception as e:
        print(f"解析训练日志时出错: {e}")
        return None

def display_progress(progress):
    """显示训练进度"""
    if not progress:
        print("❌ 无法获取训练进度")
        return
    
    print("="*60)
    print("方案F训练进度（state_vec编码修复后）")
    print("="*60)
    print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    print(f"训练进度: Epoch {progress['current_epoch']}/{progress['total_epochs']} ({progress['progress_percent']:.1f}%)")
    
    if progress['loss'] is not None:
        print(f"当前损失: {progress['loss']:.4f}")
    if progress['exact_accuracy'] is not None:
        print(f"完全匹配准确率: {progress['exact_accuracy']:.2f}%")
    if progress['card_accuracy'] is not None:
        print(f"卡牌级别准确率: {progress['card_accuracy']:.2f}%")
    if progress['learning_rate'] is not None:
        print(f"学习率: {progress['learning_rate']:.6f}")
    
    print()
    if progress['completed']:
        print("✅ 训练已完成！")
    else:
        remaining_epochs = progress['total_epochs'] - progress['current_epoch']
        print(f"⏳ 剩余轮数: {remaining_epochs} epochs")
        print(f"预计剩余时间: 约 {remaining_epochs * 2:.0f} 分钟（假设每epoch约2分钟）")
    
    print()
    print("最新日志:")
    print(f"  {progress['last_line']}")
    print("="*60)

def main():
    log_file = find_latest_training_log()
    if not log_file:
        print("❌ 未找到训练日志文件")
        return
    
    print(f"日志文件: {log_file}")
    print()
    
    progress = parse_training_progress(log_file)
    display_progress(progress)

if __name__ == "__main__":
    main()

