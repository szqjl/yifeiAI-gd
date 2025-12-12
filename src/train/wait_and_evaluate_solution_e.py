# -*- coding: utf-8 -*-
"""
等待方案E训练完成并自动评估
方案E：改进训练策略（增加训练轮数到250）
"""

import os
import time
import subprocess
import glob
from datetime import datetime

def find_latest_training_log():
    """找到最新的训练日志文件"""
    log_files = glob.glob("training_logs/solution_e_training_*.log")
    if not log_files:
        return None
    return max(log_files, key=os.path.getmtime)

def check_training_complete(log_file):
    """检查训练是否完成"""
    if not os.path.exists(log_file):
        return False
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            if not lines:
                return False
            
            # 检查最后几行是否包含训练完成的关键词
            last_lines = ''.join(lines[-10:])
            if 'Training completed' in last_lines or 'Epoch 250/250' in last_lines:
                return True
            if '保存模型' in last_lines or 'Model saved' in last_lines:
                return True
    except Exception as e:
        print(f"检查训练日志时出错: {e}")
        return False
    
    return False

def evaluate_model():
    """评估模型"""
    print("\n" + "="*60)
    print("开始评估方案E模型...")
    print("="*60)
    
    # 使用基线参数评估
    cmd = [
        "python", "src/train/evaluate_baseline.py",
        "--model", "models/bc_model_v1.pth",
        "--data", "game_records",
        "--max-samples", "796"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        print(result.stdout)
        if result.stderr:
            print("错误输出:", result.stderr)
        
        # 保存评估结果
        result_file = f"training_logs/solution_e_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(result_file, 'w', encoding='utf-8') as f:
            f.write("方案E评估结果\n")
            f.write("="*60 + "\n")
            f.write(f"评估时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*60 + "\n\n")
            f.write(result.stdout)
            if result.stderr:
                f.write("\n错误输出:\n")
                f.write(result.stderr)
        
        print(f"\n评估结果已保存到: {result_file}")
        return True
    except Exception as e:
        print(f"评估模型时出错: {e}")
        return False

def main():
    print("="*60)
    print("方案E训练监控脚本")
    print("="*60)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n等待训练完成...")
    print("（每30秒检查一次训练日志）")
    
    check_interval = 30  # 每30秒检查一次
    max_wait_time = 3600 * 8  # 最多等待8小时
    start_time = time.time()
    
    while True:
        elapsed_time = time.time() - start_time
        if elapsed_time > max_wait_time:
            print(f"\n等待时间超过{max_wait_time/3600:.1f}小时，停止监控")
            break
        
        log_file = find_latest_training_log()
        if log_file:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 检查训练日志: {log_file}")
            if check_training_complete(log_file):
                print("\n训练已完成！开始评估...")
                evaluate_model()
                break
            else:
                # 显示训练进度
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        if lines:
                            last_line = lines[-1].strip()
                            if last_line:
                                print(f"  最新日志: {last_line[:80]}...")
                except:
                    pass
        else:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 未找到训练日志文件，继续等待...")
        
        time.sleep(check_interval)
    
    print("\n监控脚本结束")

if __name__ == "__main__":
    main()

