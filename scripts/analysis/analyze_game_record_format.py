"""分析游戏记录格式，找出胜负信息存储位置"""
import json
from pathlib import Path
from collections import Counter

print("="*60)
print("游戏记录格式分析")
print("="*60)

game_records_dir = Path("game_records")
if not game_records_dir.exists():
    print("游戏记录目录不存在")
    exit(1)

# 查找M1相关记录
yf1_records = list(game_records_dir.glob("*yf1_m1*.json"))
print(f"\n找到 {len(yf1_records)} 个M1相关记录")

if not yf1_records:
    print("未找到M1相关记录")
    exit(1)

# 分析前5个记录
print("\n分析前5个记录的结构:")
print("-"*60)

top_level_keys = Counter()
game_info_keys = Counter()
result_keys = Counter()
has_victory_info = 0
no_victory_info = 0

for i, record_file in enumerate(yf1_records[:5]):
    print(f"\n记录 {i+1}: {record_file.name}")
    try:
        with open(record_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 统计顶层键
        for key in data.keys():
            top_level_keys[key] += 1
        
        print(f"  顶层键: {list(data.keys())[:10]}")
        
        # 检查game_info
        if 'game_info' in data:
            game_info = data['game_info']
            if isinstance(game_info, dict):
                for key in game_info.keys():
                    game_info_keys[key] += 1
                print(f"  game_info键: {list(game_info.keys())[:15]}")
                
                # 检查胜负相关字段
                for field in ['game_result', 'team_result', 'victoryNum', 'result']:
                    if field in game_info:
                        print(f"    {field}: {game_info[field]}")
                        has_victory_info += 1
            else:
                print(f"  game_info类型: {type(game_info)}")
        
        # 检查result
        if 'result' in data:
            result = data['result']
            if isinstance(result, dict):
                for key in result.keys():
                    result_keys[key] += 1
                print(f"  result键: {list(result.keys())[:15]}")
                
                # 检查victoryNum
                if 'victoryNum' in result:
                    print(f"    victoryNum: {result['victoryNum']}")
                    has_victory_info += 1
            else:
                print(f"  result类型: {type(result)}")
        
        # 如果没有找到胜负信息
        if 'game_info' not in data or 'result' not in data:
            no_victory_info += 1
        
    except Exception as e:
        print(f"  读取失败: {e}")

print("\n" + "="*60)
print("统计摘要")
print("="*60)
print(f"\n顶层键统计（前10）:")
for key, count in top_level_keys.most_common(10):
    print(f"  {key}: {count}次")

print(f"\ngame_info键统计（前10）:")
for key, count in game_info_keys.most_common(10):
    print(f"  {key}: {count}次")

print(f"\nresult键统计（前10）:")
for key, count in result_keys.most_common(10):
    print(f"  {key}: {count}次")

print(f"\n胜负信息:")
print(f"  找到胜负信息: {has_victory_info}个记录")
print(f"  无胜负信息: {no_victory_info}个记录")

# 尝试从所有记录中提取胜负信息
print("\n" + "="*60)
print("尝试从所有记录提取胜负信息")
print("="*60)

wins = 0
losses = 0
total = 0

for record_file in yf1_records[:50]:  # 分析前50个
    try:
        with open(record_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 方法1: 从game_info.game_result
        game_info = data.get('game_info', {})
        if isinstance(game_info, dict):
            game_result = game_info.get('game_result')
            if game_result == 'win':
                wins += 1
                total += 1
                continue
            elif game_result == 'loss':
                losses += 1
                total += 1
                continue
        
        # 方法2: 从game_info.team_result
        if isinstance(game_info, dict):
            team_result = game_info.get('team_result')
            if team_result == 'win':
                # player 0是Team A
                wins += 1
                total += 1
                continue
            elif team_result == 'loss':
                losses += 1
                total += 1
                continue
        
        # 方法3: 从result.victoryNum
        result = data.get('result', {})
        if isinstance(result, dict):
            victory_num = result.get('victoryNum', [])
            if victory_num and isinstance(victory_num, list) and len(victory_num) > 0:
                if victory_num[0] > 0:  # player 0获胜
                    wins += 1
                    total += 1
                else:
                    losses += 1
                    total += 1
                continue
        
    except Exception as e:
        continue

if total > 0:
    win_rate = wins / total
    print(f"\n提取结果:")
    print(f"  分析记录数: {total}")
    print(f"  胜利: {wins}")
    print(f"  失败: {losses}")
    print(f"  胜率: {win_rate:.2%}")
else:
    print(f"\n无法从记录中提取胜负信息")
    print(f"可能原因:")
    print(f"  1. 记录格式不匹配")
    print(f"  2. 胜负信息存储在其他字段")
    print(f"  3. 需要从其他来源获取胜负信息")

print("\n" + "="*60)
