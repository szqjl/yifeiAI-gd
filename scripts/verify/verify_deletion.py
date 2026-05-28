"""验证删除结果"""
from pathlib import Path

print("="*60)
print("删除结果验证")
print("="*60)

game_records_dir = Path("game_records")
if not game_records_dir.exists():
    print("游戏记录目录不存在")
    exit(1)

# 获取所有文件
all_files = list(game_records_dir.glob("*"))
replay_files = [f for f in all_files if f.name.startswith("replay") and f.is_file()]
other_files = [f for f in all_files if not f.name.startswith("replay") and f.is_file()]

print(f"\n当前状态:")
print(f"  总文件数: {len(all_files)}")
print(f"  replay文件: {len(replay_files)} (保留)")
print(f"  其他文件: {len(other_files)} (应已删除)")

if replay_files:
    print(f"\n保留的replay文件示例（前10个）:")
    for i, f in enumerate(replay_files[:10], 1):
        print(f"  {i}. {f.name}")

if other_files:
    print(f"\n警告: 仍有 {len(other_files)} 个非replay文件:")
    for i, f in enumerate(other_files[:10], 1):
        print(f"  {i}. {f.name}")
    if len(other_files) > 10:
        print(f"  ... 还有 {len(other_files) - 10} 个文件")
else:
    print(f"\n[OK] 所有非replay文件已成功删除")

print("="*60)
