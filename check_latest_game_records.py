"""检查最新游戏记录的胜负信息"""
import json
from pathlib import Path
from datetime import datetime

print("="*60)
print("最新游戏记录胜负信息检查")
print("="*60)

game_records_dir = Path("game_records")
if not game_records_dir.exists():
    print("游戏记录目录不存在")
    exit(1)

# 查找M1相关记录
yf1_records = list(game_records_dir.glob("*yf1_m1*.json"))
if not yf1_records:
    print("未找到M1相关记录")
    exit(1)

# 按修改时间排序，获取最新的10条记录
latest_records = sorted(yf1_records, key=lambda p: p.stat().st_mtime, reverse=True)[:10]

print(f"\n检查最新 {len(latest_records)} 条记录:")
print("-"*60)

has_victory_num = 0
no_victory_num = 0

for i, record_file in enumerate(latest_records, 1):
    try:
        with open(record_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        mtime = datetime.fromtimestamp(record_file.stat().st_mtime)
        
        print(f"\n记录 {i}: {record_file.name}")
        print(f"  时间: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 检查result字段
        result = data.get('result', {})
        
        if isinstance(result, dict):
            if 'victoryNum' in result:
                victory_num = result['victoryNum']
                print(f"  [OK] 包含victoryNum: {victory_num}")
                
                # 分析胜负（player 0是yf1_m1）
                if isinstance(victory_num, list) and len(victory_num) > 0:
                    player0_wins = victory_num[0] if victory_num[0] > 0 else 0
                    player1_wins = victory_num[1] if len(victory_num) > 1 and victory_num[1] > 0 else 0
                    player2_wins = victory_num[2] if len(victory_num) > 2 and victory_num[2] > 0 else 0
                    player3_wins = victory_num[3] if len(victory_num) > 3 and victory_num[3] > 0 else 0
                    
                    print(f"    玩家0 (yf1_m1): {player0_wins}胜")
                    print(f"    玩家1: {player1_wins}胜")
                    print(f"    玩家2 (yf2_m1): {player2_wins}胜")
                    print(f"    玩家3: {player3_wins}胜")
                    
                    # 判断Team A (0和2) vs Team B (1和3)
                    team_a_wins = player0_wins + player2_wins
                    team_b_wins = player1_wins + player3_wins
                    
                    if team_a_wins > team_b_wins:
                        print(f"    结果: Team A (M1队伍) 获胜")
                    elif team_b_wins > team_a_wins:
                        print(f"    结果: Team B 获胜")
                    else:
                        print(f"    结果: 平局")
                
                has_victory_num += 1
            else:
                print(f"  [WARN] result字段存在，但缺少victoryNum")
                print(f"  result内容: {result}")
                no_victory_num += 1
        else:
            print(f"  [ERROR] result字段不是字典: {type(result)}")
            print(f"  result内容: {result}")
            no_victory_num += 1
            
    except Exception as e:
        print(f"  [ERROR] 读取失败: {e}")
        no_victory_num += 1

print("\n" + "="*60)
print("统计摘要")
print("="*60)
print(f"检查记录数: {len(latest_records)}")
print(f"包含victoryNum: {has_victory_num}条")
print(f"缺少victoryNum: {no_victory_num}条")

if has_victory_num > 0:
    print(f"\n[成功] 修复生效！{has_victory_num}条记录包含victoryNum信息")
    print("评估器现在可以正确计算胜率了")
else:
    print(f"\n[警告] 所有记录都缺少victoryNum信息")
    print("可能原因：")
    print("  1. 修复未生效（需要重启客户端）")
    print("  2. 游戏记录在修复前生成")
    print("  3. 服务器未发送gameResult通知")

print("="*60)
