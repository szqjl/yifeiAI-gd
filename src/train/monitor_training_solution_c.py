# -*- coding: utf-8 -*-
"""
监控方案C训练进度，训练完成后自动评估并记录结果
"""

import sys
import os
import time
import subprocess
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

def check_training_complete(log_file="training_logs/solution_c_training_20251210.log"):
    """检查训练是否完成"""
    if not os.path.exists(log_file):
        return False
    
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        # 检查是否包含训练完成的关键词
        if "Training completed" in content or "Epoch 150/150" in content:
            return True
        # 检查最后一行是否包含epoch信息
        lines = content.strip().split('\n')
        if lines:
            last_line = lines[-1]
            if "Epoch 150/150" in last_line or "训练完成" in last_line:
                return True
    return False

def wait_for_training_complete(log_file="training_logs/solution_c_training_20251210.log", 
                               max_wait_hours=3, check_interval=60):
    """等待训练完成"""
    print(f"等待训练完成... (最多等待{max_wait_hours}小时)")
    start_time = time.time()
    max_wait_seconds = max_wait_hours * 3600
    
    while time.time() - start_time < max_wait_seconds:
        if check_training_complete(log_file):
            print("训练已完成！")
            return True
        
        # 显示当前进度
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                if lines:
                    # 查找最后一个epoch信息
                    for line in reversed(lines):
                        if "Epoch" in line and "/150" in line:
                            print(f"当前进度: {line.strip()}")
                            break
        
        time.sleep(check_interval)
    
    print(f"等待超时（{max_wait_hours}小时），检查训练状态...")
    return False

def evaluate_solution_c():
    """评估方案C的训练结果"""
    print("\n" + "="*60)
    print("评估方案C训练结果")
    print("="*60)
    
    # 使用最新的模型文件
    model_file = "models/bc_model_v1.pth"
    if not os.path.exists(model_file):
        # 查找最新的epoch模型
        import glob
        epoch_models = sorted(glob.glob("models/bc_model_v1_epoch_*.pth"), 
                             key=os.path.getmtime, reverse=True)
        if epoch_models:
            model_file = epoch_models[0]
            print(f"使用模型文件: {model_file}")
        else:
            print("错误：找不到模型文件")
            return None
    
    # 运行评估脚本
    print(f"\n使用基线参数评估模型: {model_file}")
    result = subprocess.run(
        ["python", "src/train/evaluate_baseline.py", 
         "--model", model_file, 
         "--data", "game_records",
         "--max-samples", "796"],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='ignore'
    )
    
    print(result.stdout)
    if result.stderr:
        print("错误输出:", result.stderr)
    
    return result.stdout

if __name__ == "__main__":
    log_file = "training_logs/solution_c_training_20251210.log"
    
    # 等待训练完成
    if wait_for_training_complete(log_file, max_wait_hours=3):
        # 评估结果
        eval_result = evaluate_solution_c()
        
        # 保存评估结果
        result_file = f"training_logs/solution_c_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(result_file, 'w', encoding='utf-8') as f:
            f.write(f"方案C训练评估结果\n")
            f.write(f"评估时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*60 + "\n")
            f.write(eval_result)
        
        print(f"\n评估结果已保存到: {result_file}")
    else:
        print("\n训练可能仍在进行中，请稍后手动评估")

