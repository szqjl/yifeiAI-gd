"""检查自动重启系统状态"""
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

print("="*60)
print("自动重启系统状态检查")
print("="*60)

# 检查工作流状态
status_file = Path("models/m1_workflow_status.json")
if status_file.exists():
    with open(status_file, 'r', encoding='utf-8') as f:
        status = json.load(f)
    print(f"\n工作流状态: {status.get('status')}")
    print(f"当前迭代: {status.get('current_iteration', 0)}/{status.get('max_iterations', 10)}")
    print(f"成功: {'是' if status.get('success') else '否'}")
    timestamp = status.get('timestamp', '')
    if timestamp:
        print(f"最后更新: {timestamp[:19]}")

# 检查是否有Python进程在运行auto_restart_workflow
print("\n检查自动重启系统进程...")
try:
    result = subprocess.run(
        ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'],
        capture_output=True,
        text=True,
        encoding='gbk',
        errors='replace'
    )
    if 'auto_restart_workflow' in result.stdout or 'auto_restart' in result.stdout:
        print("  [运行中] 自动重启系统进程已找到")
    else:
        print("  [未运行] 未找到自动重启系统进程")
        print("  提示: 运行 'python auto_restart_workflow.py' 启动系统")
except Exception as e:
    print(f"  无法检查进程状态: {e}")

# 检查训练代码是否已被改进
print("\n检查训练代码改进状态...")
code_file = Path("src/train/stage7_optimized_training.py")
if code_file.exists():
    with open(code_file, 'r', encoding='utf-8') as f:
        code = f.read()
    
    improvements = []
    if "threshold = torch.clamp(base_threshold * 0.001, 0.0001, 0.01)" in code:
        improvements.append("✓ 阈值已改进（0.0001-0.01）")
    elif "threshold = torch.clamp(base_threshold * 0.01, 0.001, 0.1)" in code:
        improvements.append("⚠ 阈值仍需改进（当前0.001-0.1）")
    
    if "over_prediction_penalty=5000.0" in code:
        improvements.append("✓ 过度预测惩罚已增加（5000.0）")
    elif "over_prediction_penalty=1000.0" in code:
        improvements.append("⚠ 过度预测惩罚仍需增加（当前1000.0）")
    
    if "learning_rate: float = 0.00001" in code:
        improvements.append("✓ 学习率已降低（0.00001）")
    elif "learning_rate: float = 0.00005" in code:
        improvements.append("⚠ 学习率仍需降低（当前0.00005）")
    
    if improvements:
        print("  改进状态:")
        for imp in improvements:
            # 替换特殊字符避免编码错误
            imp_safe = imp.replace('✓', '[OK]').replace('⚠', '[WARN]')
            print(f"    {imp_safe}")
    else:
        print("  未检测到改进")

# 检查备份文件
print("\n检查代码备份...")
backup_files = list(Path("src/train").glob("stage7_optimized_training.py.backup_*"))
if backup_files:
    print(f"  找到 {len(backup_files)} 个备份文件")
    latest_backup = max(backup_files, key=lambda p: p.stat().st_mtime)
    mtime = datetime.fromtimestamp(latest_backup.stat().st_mtime)
    print(f"  最新备份: {latest_backup.name}")
    print(f"  备份时间: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
else:
    print("  未找到备份文件（代码可能尚未被改进）")

print("\n" + "="*60)
print("提示:")
print("  - 运行 'python monitor_workflow_progress.py' 查看训练进度")
print("  - 运行 'python check_workflow_status.py' 查看工作流状态")
print("  - 运行 'python auto_restart_workflow.py' 启动自动重启系统")
print("="*60)
