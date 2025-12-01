# -*- coding: utf-8 -*-
"""
游戏回放工具 - 加载并回放保存的游戏记录
"""

import json
import sys
from pathlib import Path
from typing import Dict
from communication.game_recorder import GameRecorder


def list_games(record_dir: Path = None):
    """列出所有游戏记录"""
    if record_dir is None:
        record_dir = Path(__file__).parent.parent.parent / "game_records"
    
    if not record_dir.exists():
        print(f"游戏记录目录不存在: {record_dir}")
        return []
    
    games = list(record_dir.glob("*.json"))
    games.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    return games


def replay_game_file(filepath: Path, verbose: bool = True, analyze_rules: bool = True):
    """回放指定的游戏文件"""
    if not filepath.exists():
        print(f"文件不存在: {filepath}")
        return
    
    game_data = GameRecorder.load_game(filepath)
    GameRecorder.replay_game(game_data, verbose, analyze_rules)
    
    # 分析规则使用情况
    if analyze_rules:
        analyze_rule_usage(game_data)


def analyze_rule_usage(game_data: Dict):
    """分析规则使用情况"""
    print("\n" + "=" * 80)
    print("【规则使用分析】")
    print("-" * 80)
    
    my_pos = game_data['player_id']
    teammate_pos = (my_pos + 2) % 4
    actions = game_data.get('actions', [])
    my_decisions = game_data.get('my_decisions', [])
    
    # 分析关键规则违反情况
    violations = []
    
    for i, action in enumerate(actions):
        cur_pos = action['cur_pos']
        cur_action = action['cur_action']
        greater_pos = action['greater_pos']
        
        # 只分析我方的决策
        if cur_pos != my_pos:
            continue
        
        if not cur_action or len(cur_action) == 0 or cur_action[0] == "PASS":
            continue
        
        action_type = cur_action[0]
        
        # 规则1: 队友控场时不应该用炸弹压队友
        if greater_pos == teammate_pos and action_type == "Bomb":
            violations.append({
                "step": i + 1,
                "rule": "队友保护规则",
                "violation": "用炸弹压队友",
                "action": cur_action,
                "context": f"队友{teammate_pos}号位控场"
            })
        
        # 规则2: 开局阶段不应该越级打大牌
        if i < 20:  # 前20步算开局
            if action_type == "Single" and len(cur_action) > 1:
                rank = cur_action[1]
                # 检查前一步的牌值
                if i > 0:
                    prev_action = actions[i-1]
                    if prev_action.get('cur_action') and len(prev_action['cur_action']) > 1:
                        prev_rank = prev_action['cur_action'][1]
                        # 简单判断：如果从6跳到A，可能是越级
                        rank_values = {'3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, 
                                      '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 
                                      'A': 14, '2': 15, 'B': 16, 'R': 17}
                        if rank in rank_values and prev_rank in rank_values:
                            if rank_values[rank] - rank_values[prev_rank] > 5:
                                violations.append({
                                    "step": i + 1,
                                    "rule": "开局策略",
                                    "violation": "越级打大牌",
                                    "action": cur_action,
                                    "context": f"从{prev_rank}跳到{rank}"
                                })
    
    if violations:
        print(f"发现 {len(violations)} 处可能的规则违反:")
        for v in violations:
            print(f"  步骤{v['step']}: {v['violation']} ({v['rule']})")
            print(f"    动作: {v['action']}")
            print(f"    上下文: {v['context']}")
    else:
        print("未发现明显的规则违反")
    
    print("=" * 80)


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法:")
        print("  python replay_game.py <game_file>  # 回放指定游戏")
        print("  python replay_game.py <game_file> --no-analyze  # 回放但不分析规则")
        print("  python replay_game.py --list       # 列出所有游戏记录")
        return
    
    if sys.argv[1] == "--list":
        games = list_games()
        print(f"\n找到 {len(games)} 个游戏记录:\n")
        for i, game_file in enumerate(games[:20], 1):  # 只显示最近20个
            print(f"{i}. {game_file.name}")
            print(f"   时间: {game_file.stat().st_mtime}")
        return
    
    # 回放指定游戏
    filepath = Path(sys.argv[1])
    if not filepath.is_absolute():
        # 相对路径，尝试在game_records目录中查找
        record_dir = Path(__file__).parent.parent.parent / "game_records"
        filepath = record_dir / sys.argv[1]
    
    replay_game_file(filepath)


if __name__ == "__main__":
    main()

