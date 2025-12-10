# -*- coding: utf-8 -*-
"""
等待方案C训练完成，然后评估并记录结果
"""

import sys
import os
import time
import subprocess
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

def get_current_epoch(log_file):
    """获取当前训练epoch"""
    if not os.path.exists(log_file):
        return 0
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            for line in reversed(lines):
                if "Epoch" in line and "/150" in line:
                    # 提取epoch数字
                    import re
                    match = re.search(r'Epoch (\d+)/150', line)
                    if match:
                        return int(match.group(1))
    except:
        pass
    return 0

def wait_for_training_complete(log_file="training_logs/solution_c_training_20251210.log", 
                               max_wait_minutes=180):
    """等待训练完成"""
    print(f"等待训练完成... (最多等待{max_wait_minutes}分钟)")
    start_time = time.time()
    max_wait_seconds = max_wait_minutes * 60
    last_epoch = 0
    
    while time.time() - start_time < max_wait_seconds:
        current_epoch = get_current_epoch(log_file)
        
        if current_epoch >= 150:
            print(f"训练已完成！(Epoch {current_epoch}/150)")
            return True
        
        if current_epoch > last_epoch:
            elapsed = int(time.time() - start_time)
            print(f"[{elapsed//60}分{elapsed%60}秒] 当前进度: Epoch {current_epoch}/150")
            last_epoch = current_epoch
        
        time.sleep(30)  # 每30秒检查一次
    
    print(f"等待超时（{max_wait_minutes}分钟），当前进度: Epoch {get_current_epoch(log_file)}/150")
    return False

def evaluate_solution_c():
    """评估方案C的训练结果"""
    print("\n" + "="*60)
    print("评估方案C训练结果")
    print("="*60)
    
    # 使用最新的模型文件
    model_file = "models/bc_model_v1.pth"
    if not os.path.exists(model_file):
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
    if wait_for_training_complete(log_file, max_wait_minutes=180):
        # 等待几秒确保文件写入完成
        time.sleep(5)
        
        # 评估结果
        eval_result = evaluate_solution_c()
        
        if eval_result:
            # 保存评估结果
            result_file = f"training_logs/solution_c_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(f"方案C训练评估结果\n")
                f.write(f"评估时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*60 + "\n")
                f.write(eval_result)
            
            print(f"\n评估结果已保存到: {result_file}")
            print("\n请查看评估结果并更新阶段0文档")
    else:
        print("\n训练可能仍在进行中，请稍后手动运行评估")

