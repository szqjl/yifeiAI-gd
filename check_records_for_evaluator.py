"""检查游戏记录是否满足评估器需求"""
import json
from pathlib import Path
from datetime import datetime

print("="*60)
print("游戏记录评估器兼容性检查")
print("="*60)

game_records_dir = Path("game_records")
if not game_records_dir.exists():
    print("游戏记录目录不存在")
    exit(1)

# 获取所有记录文件
all_records = list(game_records_dir.glob("*.json"))
print(f"\n总记录数: {len(all_records)}")

# 检查M1相关记录（yf1_m1或yf2_m1）
m1_records = [r for r in all_records if "yf1_m1" in r.name or "yf2_m1" in r.name]
print(f"M1相关记录: {len(m1_records)}")

if not m1_records:
    print("\n[警告] 未找到M1相关记录")
    print("评估器需要包含yf1_m1或yf2_m1的记录")
    exit(1)

# 按修改时间排序，检查最新的10条
latest_records = sorted(m1_records, key=lambda p: p.stat().st_mtime, reverse=True)[:10]

print(f"\n检查最新 {len(latest_records)} 条M1记录:")
print("-"*60)

evaluator_compatible = 0
not_compatible = 0
compatibility_issues = []

for i, record_file in enumerate(latest_records, 1):
    try:
        with open(record_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        mtime = datetime.fromtimestamp(record_file.stat().st_mtime)
        
        print(f"\n记录 {i}: {record_file.name}")
        print(f"  时间: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 检查评估器需要的字段
        issues = []
        
        # 1. 检查result字段
        result = data.get('result', {})
        if not result:
            issues.append("缺少result字段")
        elif not isinstance(result, dict):
            issues.append(f"result不是字典: {type(result)}")
        else:
            # 2. 检查victoryNum
            if 'victoryNum' not in result:
                issues.append("result中缺少victoryNum")
            else:
                victory_num = result['victoryNum']
                if not isinstance(victory_num, list):
                    issues.append(f"victoryNum不是列表: {type(victory_num)}")
                elif len(victory_num) < 4:
                    issues.append(f"victoryNum长度不足: {len(victory_num)}")
                else:
                    print(f"  [OK] victoryNum: {victory_num}")
        
        # 3. 检查player_id
        player_id = data.get('player_id')
        if player_id is None:
            issues.append("缺少player_id")
        else:
            print(f"  [OK] player_id: {player_id}")
        
        # 4. 检查game_info（可选，但评估器会尝试使用）
        game_info = data.get('game_info', {})
        if game_info:
            print(f"  [OK] game_info存在")
        
        if issues:
            print(f"  [问题] {', '.join(issues)}")
            not_compatible += 1
            compatibility_issues.extend(issues)
        else:
            print(f"  [OK] 满足评估器要求")
            evaluator_compatible += 1
            
    except Exception as e:
        print(f"  [错误] 读取失败: {e}")
        not_compatible += 1

print("\n" + "="*60)
print("兼容性统计")
print("="*60)
print(f"检查记录数: {len(latest_records)}")
print(f"满足要求: {evaluator_compatible}条")
print(f"不满足要求: {not_compatible}条")

if evaluator_compatible > 0:
    print(f"\n[成功] {evaluator_compatible}条记录满足评估器要求")
    print("评估器可以正确提取胜负信息")
else:
    print(f"\n[警告] 没有记录满足评估器要求")
    print("可能原因：")
    for issue in set(compatibility_issues):
        print(f"  - {issue}")

# 测试评估器
print("\n" + "="*60)
print("测试评估器")
print("="*60)

try:
    from src.train.m1_vs_client_evaluator import M1VsClientEvaluator
    
    evaluator = M1VsClientEvaluator()
    result = evaluator.evaluate_win_rate(num_games=10, opponent_type="client", player_id=0)
    
    print(f"评估结果:")
    print(f"  胜率: {result.get('win_rate', 0):.2%}")
    print(f"  总对局: {result.get('total_games', 0)}")
    print(f"  胜利: {result.get('wins', 0)}")
    print(f"  失败: {result.get('losses', 0)}")
    print(f"  状态: {result.get('status', 'unknown')}")
    
    if result.get('status') == 'success':
        print(f"\n[成功] 评估器可以正常工作")
    else:
        print(f"\n[警告] 评估器状态: {result.get('status')}")
        if result.get('message'):
            print(f"  消息: {result.get('message')}")
            
except Exception as e:
    print(f"[错误] 评估器测试失败: {e}")
    import traceback
    traceback.print_exc()

print("="*60)
