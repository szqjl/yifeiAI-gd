"""
检查工作流通知状态
"""

import json
from pathlib import Path
import sys

# 设置编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def check_workflow_status():
    """检查工作流状态和通知"""
    print("="*60)
    print("M1训练工作流状态检查")
    print("="*60)
    
    # 检查成功标记
    success_file = Path("models/M1_TARGET_ACHIEVED.txt")
    if success_file.exists():
        print("\n🎉 目标已达成！")
        print(f"查看详情: {success_file}")
        with open(success_file, 'r', encoding='utf-8') as f:
            print("\n" + f.read())
        return
    
    # 检查未完成标记
    incomplete_file = Path("models/M1_TARGET_NOT_ACHIEVED.txt")
    if incomplete_file.exists():
        print("\n⚠️ 目标未完全达成")
        print(f"查看详情: {incomplete_file}")
        with open(incomplete_file, 'r', encoding='utf-8') as f:
            print("\n" + f.read())
    
    # 检查工作流历史
    history_file = Path("models/m1_training_workflow_history.json")
    if history_file.exists():
        print("\n📊 工作流历史:")
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            print(f"  目标胜率: {data.get('target_win_rate', 0):.1%}")
            print(f"  最大迭代: {data.get('max_iterations', 0)}")
            print(f"  最终状态: {data.get('final_status', 'unknown')}")
            
            history = data.get('workflow_history', [])
            if history:
                print(f"\n  迭代记录 ({len(history)} 次):")
                for i, record in enumerate(history[-5:], 1):  # 显示最近5次
                    win_rate = record.get('win_rate', 0)
                    iteration = record.get('iteration', 0)
                    timestamp = record.get('timestamp', '')
                    print(f"    迭代 {iteration}: 胜率 {win_rate:.2%} ({timestamp[:19]})")
                
                last_record = history[-1]
                last_win_rate = last_record.get('win_rate', 0)
                target = data.get('target_win_rate', 0.5)
                
                if last_win_rate >= target:
                    print(f"\n  ✅ 当前胜率 ({last_win_rate:.2%}) 已达到目标 ({target:.1%})")
                else:
                    gap = target - last_win_rate
                    print(f"\n  ⚠️ 当前胜率 ({last_win_rate:.2%}) 距离目标 ({target:.1%}) 还差 {gap:.2%}")
        except Exception as e:
            print(f"  读取历史失败: {e}")
    else:
        print("\n⚠️ 工作流历史文件不存在，工作流可能尚未运行")
    
    # 检查状态文件
    status_file = Path("models/m1_workflow_status.txt")
    if status_file.exists():
        print("\n📋 当前状态:")
        with open(status_file, 'r', encoding='utf-8') as f:
            print(f.read())
    
    print("\n" + "="*60)
    print("检查完成")
    print("="*60)

if __name__ == "__main__":
    check_workflow_status()
