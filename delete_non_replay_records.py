"""删除game_records目录中不以replay开头的记录，保留replay开头的记录"""
from pathlib import Path
import json

print("="*60)
print("删除非replay游戏记录")
print("="*60)

game_records_dir = Path("game_records")
if not game_records_dir.exists():
    print("游戏记录目录不存在")
    exit(1)

# 获取所有文件
all_files = list(game_records_dir.glob("*"))
replay_files = [f for f in all_files if f.name.startswith("replay")]
other_files = [f for f in all_files if not f.name.startswith("replay") and f.is_file()]

print(f"\n统计:")
print(f"  总文件数: {len(all_files)}")
print(f"  replay开头文件: {len(replay_files)} (将保留)")
print(f"  其他文件: {len(other_files)} (将删除)")

if not other_files:
    print("\n没有需要删除的文件")
    exit(0)

# 确认删除
print(f"\n准备删除 {len(other_files)} 个文件:")
for i, f in enumerate(other_files[:10], 1):
    print(f"  {i}. {f.name}")
if len(other_files) > 10:
    print(f"  ... 还有 {len(other_files) - 10} 个文件")

# 执行删除
deleted_count = 0
failed_count = 0

for file_path in other_files:
    try:
        file_path.unlink()
        deleted_count += 1
    except Exception as e:
        print(f"删除失败 {file_path.name}: {e}")
        failed_count += 1

print("\n" + "="*60)
print("删除完成")
print("="*60)
print(f"成功删除: {deleted_count} 个文件")
print(f"删除失败: {failed_count} 个文件")
print(f"保留replay文件: {len(replay_files)} 个")

# 验证
remaining_files = list(game_records_dir.glob("*"))
remaining_non_replay = [f for f in remaining_files if not f.name.startswith("replay") and f.is_file()]
if remaining_non_replay:
    print(f"\n警告: 仍有 {len(remaining_non_replay)} 个非replay文件未删除")
else:
    print(f"\n[OK] 所有非replay文件已删除")

print("="*60)
