#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练进度监控脚本
实时显示训练进度、损失、准确率等信息
"""

import os
import time
import glob
from datetime import datetime
from pathlib import Path

def get_latest_log_file():
    """获取最新的训练日志文件"""
    log_dir = Path("training_logs")
    if not log_dir.exists():
        return None
    
    log_files = list(log_dir.glob("strategy_tasks_training_*.log"))
    if not log_files:
        return None
    
    # 返回最新的日志文件
    return max(log_files, key=lambda f: f.stat().st_mtime)

def get_latest_model_checkpoint():
    """获取最新的模型检查点"""
    model_dir = Path("models")
    if not model_dir.exists():
        return None
    
    checkpoints = list(model_dir.glob("bc_model_strategy_tasks_epoch_*.pth"))
    if not checkpoints:
        return None
    
    # 返回最新的检查点
    return max(checkpoints, key=lambda f: f.stat().st_mtime)

def monitor_training():
    """监控训练进度"""
    print("="*80)
    print("训练进度监控")
    print("="*80)
    print(f"开始监控时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    last_epoch = -1
    last_checkpoint = None
    
    while True:
        try:
            # 检查训练进程是否还在运行
            import subprocess
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"],
                capture_output=True,
                text=True,
                shell=True
            )
            
            # 检查是否有train_strategy_tasks.py进程
            has_training_process = "train_strategy_tasks.py" in result.stdout or "train_strategy_tasks" in result.stdout
            
            # 检查最新的日志文件
            log_file = get_latest_log_file()
            if log_file:
                print(f"[日志文件] {log_file.name}")
                print(f"  大小: {log_file.stat().st_size / 1024:.2f} KB")
                print(f"  修改时间: {datetime.fromtimestamp(log_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
                
                # 读取最后几行日志
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        if lines:
                            print(f"\n[最新日志输出] (最后10行)")
                            for line in lines[-10:]:
                                print(f"  {line.rstrip()}")
                except Exception as e:
                    print(f"  读取日志失败: {e}")
            else:
                print("[日志文件] 未找到训练日志")
            
            print()
            
            # 检查最新的模型检查点
            checkpoint = get_latest_model_checkpoint()
            if checkpoint:
                if checkpoint != last_checkpoint:
                    print(f"[模型检查点] 发现新检查点: {checkpoint.name}")
                    print(f"  大小: {checkpoint.stat().st_size / (1024*1024):.2f} MB")
                    print(f"  修改时间: {datetime.fromtimestamp(checkpoint.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
                    last_checkpoint = checkpoint
                else:
                    print(f"[模型检查点] 最新: {checkpoint.name}")
            else:
                print("[模型检查点] 尚未生成检查点")
            
            print()
            
            # 检查训练进程状态
            if has_training_process:
                print("[训练状态] ✓ 训练进程正在运行")
            else:
                print("[训练状态] ✗ 训练进程可能已结束或未启动")
            
            print()
            print("-"*80)
            print(f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("按 Ctrl+C 退出监控")
            print("-"*80)
            print()
            
            # 等待5秒后再次检查
            time.sleep(5)
            
        except KeyboardInterrupt:
            print("\n监控已停止")
            break
        except Exception as e:
            print(f"监控过程中发生错误: {e}")
            time.sleep(5)

if __name__ == "__main__":
    monitor_training()

