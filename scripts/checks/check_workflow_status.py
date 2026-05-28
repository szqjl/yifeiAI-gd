"""
检查M1训练工作流状态
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# 设置输出编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def check_workflow_status():
    """检查工作流状态"""
    print("="*60)
    print("M1训练工作流状态检查")
    print("="*60)
    
    # 检查工作流历史
    history_file = Path("models/m1_training_workflow_history.json")
    if history_file.exists():
        print("\n✅ 工作流历史文件存在")
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            history = data.get('workflow_history', [])
            if history:
                print(f"\n已完成迭代: {len(history)}")
                print(f"目标胜率: {data.get('target_win_rate', 0)*100:.1f}%")
                print(f"最终状态: {data.get('final_status', 'unknown')}")
                
                if history:
                    last = history[-1]
                    print(f"\n最新迭代结果:")
                    print(f"  迭代次数: {last.get('iteration', 'N/A')}")
                    print(f"  胜率: {last.get('win_rate', 0)*100:.2f}%")
                    print(f"  时间: {last.get('timestamp', 'N/A')}")
            else:
                print("\n⚠️ 工作流历史为空")
        except Exception as e:
            print(f"\n❌ 读取工作流历史失败: {e}")
    else:
        print("\n⚠️ 工作流历史文件不存在（工作流可能未运行或刚开始）")
    
    # 检查模型文件
    model_file = Path("models/bc_model_stage7_optimized.pth")
    if model_file.exists():
        size_mb = model_file.stat().st_size / (1024 * 1024)
        print(f"\n✅ 模型文件存在: {model_file.name} ({size_mb:.2f} MB)")
    else:
        print(f"\n⚠️ 模型文件不存在: {model_file.name}")
    
    # 检查训练历史
    history_file = Path("models/bc_model_stage7_optimized_training_history.json")
    if history_file.exists():
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            if history:
                last_epoch = history[-1]
                print(f"\n✅ 训练历史存在")
                print(f"  训练轮数: {len(history)}")
                print(f"  最终损失: {last_epoch.get('total_loss', 0):.2f}")
                print(f"  预测比例: {last_epoch.get('prediction_ratio', 0):.2f}")
        except Exception as e:
            print(f"\n⚠️ 读取训练历史失败: {e}")
    else:
        print(f"\n⚠️ 训练历史文件不存在")
    
    print("\n" + "="*60)
    print("检查完成")
    print("="*60)

if __name__ == "__main__":
    check_workflow_status()
