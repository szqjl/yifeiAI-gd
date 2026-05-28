"""检查模型战绩"""
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

print("="*60)
print("M1模型战绩详细报告")
print("="*60)

# 1. 工作流历史战绩
print("\n1. 工作流迭代战绩")
print("-"*60)
workflow_file = Path("models/m1_training_workflow_history.json")
if workflow_file.exists():
    with open(workflow_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    history = data.get('workflow_history', [])
    target_win_rate = data.get('target_win_rate', 0.5)
    
    print(f"目标胜率: {target_win_rate*100:.1f}%")
    print(f"总迭代次数: {len(history)}")
    
    if history:
        # 统计各状态
        status_count = defaultdict(int)
        win_rates = []
        
        print("\n迭代详情:")
        for i in history:
            iter_num = i.get('iteration', 0)
            win_rate = i.get('win_rate', 0)
            status = i.get('status', 'unknown')
            timestamp = i.get('timestamp', '')[:19]
            
            status_count[status] += 1
            if win_rate > 0:
                win_rates.append(win_rate)
            
            status_icon = "[成功]" if status == "success" else "[失败]" if status == "evaluation_failed" else "[其他]"
            print(f"  迭代{iter_num}: 胜率={win_rate:.2%} {status_icon} 时间={timestamp}")
        
        print(f"\n状态统计:")
        for status, count in status_count.items():
            print(f"  {status}: {count}次")
        
        if win_rates:
            avg_win_rate = sum(win_rates) / len(win_rates)
            max_win_rate = max(win_rates)
            print(f"\n胜率统计:")
            print(f"  平均胜率: {avg_win_rate:.2%}")
            print(f"  最高胜率: {max_win_rate:.2%}")
            print(f"  有效评估次数: {len(win_rates)}")
        else:
            print(f"\n胜率统计:")
            print(f"  所有迭代评估失败，无法计算胜率")
        
        latest = history[-1]
        print(f"\n最新战绩:")
        print(f"  迭代: {latest.get('iteration')}")
        print(f"  胜率: {latest.get('win_rate', 0):.2%}")
        print(f"  状态: {latest.get('status', 'unknown')}")
        print(f"  时间: {latest.get('timestamp', 'unknown')[:19]}")

# 2. 游戏记录统计
print("\n2. 游戏记录统计")
print("-"*60)
game_records_dir = Path("game_records")
if game_records_dir.exists():
    all_records = list(game_records_dir.glob("*.json"))
    yf1_records = list(game_records_dir.glob("*yf1_m1*.json"))
    
    print(f"总游戏记录: {len(all_records)}")
    print(f"M1相关记录: {len(yf1_records)}")
    
    if yf1_records:
        # 分析最近的记录
        recent_records = sorted(yf1_records, key=lambda p: p.stat().st_mtime, reverse=True)[:10]
        print(f"\n最近10条记录:")
        wins = 0
        losses = 0
        analyzed = 0
        
        for record_file in recent_records:
            try:
                with open(record_file, 'r', encoding='utf-8') as f:
                    record_data = json.load(f)
                
                # 尝试提取胜负信息
                game_info = record_data.get('game_info', {})
                if isinstance(game_info, dict):
                    game_result = game_info.get('game_result')
                    team_result = game_info.get('team_result')
                    
                    if game_result == 'win':
                        wins += 1
                        analyzed += 1
                    elif game_result == 'loss':
                        losses += 1
                        analyzed += 1
                    elif team_result == 'win':
                        wins += 1
                        analyzed += 1
                    elif team_result == 'loss':
                        losses += 1
                        analyzed += 1
                
                # 尝试从result字段提取
                result = record_data.get('result', {})
                if isinstance(result, dict):
                    victory_num = result.get('victoryNum', [])
                    if victory_num and isinstance(victory_num, list) and len(victory_num) > 0:
                        if victory_num[0] > 0:  # player 0 (yf1_m1) 获胜
                            wins += 1
                            analyzed += 1
                        else:
                            losses += 1
                            analyzed += 1
            except Exception as e:
                continue
        
        if analyzed > 0:
            win_rate = wins / analyzed
            print(f"\n最近记录分析:")
            print(f"  分析记录数: {analyzed}")
            print(f"  胜利: {wins}")
            print(f"  失败: {losses}")
            print(f"  胜率: {win_rate:.2%}")
        else:
            print(f"\n无法从记录中提取胜负信息")
        
        if yf1_records:
            latest_record = max(yf1_records, key=lambda p: p.stat().st_mtime)
            mtime = datetime.fromtimestamp(latest_record.stat().st_mtime)
            print(f"\n最新记录:")
            print(f"  文件名: {latest_record.name}")
            print(f"  时间: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")

# 3. 当前工作流状态
print("\n3. 当前工作流状态")
print("-"*60)
status_file = Path("models/m1_workflow_status.json")
if status_file.exists():
    with open(status_file, 'r', encoding='utf-8') as f:
        status = json.load(f)
    print(f"状态: {status.get('status')}")
    print(f"当前迭代: {status.get('current_iteration', 0)}/{status.get('max_iterations', 10)}")
    print(f"目标胜率: {status.get('target_win_rate', 0)*100:.1f}%")
    print(f"成功: {'是' if status.get('success') else '否'}")
    timestamp = status.get('timestamp', '')
    if timestamp:
        print(f"最后更新: {timestamp[:19]}")

# 4. 训练效果
print("\n4. 最新训练效果")
print("-"*60)
training_file = Path("models/bc_model_stage7_optimized_training_history.json")
if training_file.exists():
    with open(training_file, 'r', encoding='utf-8') as f:
        history = json.load(f)
    
    if isinstance(history, list) and len(history) > 0:
        latest = history[-1]
        print(f"训练轮数: {len(history)} epochs")
        print(f"最新Epoch: {latest.get('epoch')}")
        print(f"总损失: {latest.get('total_loss', 0):,.2f}")
        print(f"预测卡牌数: {latest.get('avg_predicted_cards', 0):.2f}/512")
        print(f"真实卡牌数: {latest.get('avg_true_cards', 0):.2f}")
        print(f"预测比例: {latest.get('prediction_ratio', 0):.2f}倍")

print("\n" + "="*60)
print("报告完成")
print("="*60)
