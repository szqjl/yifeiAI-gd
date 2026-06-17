# -*- coding: utf-8 -*-
"""
交互式游戏回放工具 - 支持自动回放、停止、下一步、上一步
"""

import json
import sys
import time
from pathlib import Path
from communication.game_recorder import GameRecorder, _format_cards
from typing import Dict


class InteractiveReplay:
    """交互式回放器"""
    
    def __init__(self, game_data: Dict):
        self.game_data = game_data
        self.current_step = 0
        self.auto_play = False
        self.auto_speed = 1.0  # 自动播放速度（秒/步）
        
        # 初始化玩家剩余牌数（规则：每人27张，两副牌108张，见 docs/archive/rules/牌张与基本概念.md）
        try:
            from game_logic.guandan_constants import CARDS_PER_PLAYER
        except ImportError:
            CARDS_PER_PLAYER = 27
        self.player_cards = {0: CARDS_PER_PLAYER, 1: CARDS_PER_PLAYER, 2: CARDS_PER_PLAYER, 3: CARDS_PER_PLAYER}
        
        # 牌型统计
        self.action_type_stats = {}
        
        # 计算初始剩余牌数（如果有初始手牌信息）
        if 'initial_hand' in game_data:
            my_pos = game_data['player_id']
            initial_count = len(game_data['initial_hand'])
            self.player_cards[my_pos] = initial_count
            # 其他玩家从27开始（如果不知道确切数量）
        
        # 构建所有玩家的初始手牌集合（用于一致性检查）
        all_hands = game_data.get('all_players_hands', {})
        if not all_hands:
            # 兼容旧格式
            my_pos = game_data['player_id']
            all_hands = {my_pos: game_data.get('initial_hand', [])}
        
        # 规范化键为整数
        normalized_hands = {}
        for pos, hand_cards in all_hands.items():
            if isinstance(pos, str):
                try:
                    pos = int(pos)
                except:
                    continue
            normalized_hands[pos] = hand_cards
        
        self.all_players_hands_sets = {}
        self.all_players_hands_lists = {}  # 保存列表形式，用于追踪剩余手牌
        for pos, hand_cards in normalized_hands.items():
            self.all_players_hands_sets[pos] = self._normalize_hand_cards(hand_cards)
            # 保存规范化的手牌列表
            normalized_list = []
            for c in hand_cards:
                if isinstance(c, str):
                    normalized_list.append(c)
                elif isinstance(c, list) and len(c) >= 2:
                    normalized_list.append(f"{c[0]}{c[1]}")
            self.all_players_hands_lists[pos] = normalized_list
        
        # 保留旧的initial_hand_set以兼容
        my_pos = game_data['player_id']
        self.initial_hand_set = self.all_players_hands_sets.get(my_pos, set())
    
    def _normalize_hand_cards(self, hand_cards):
        """将手牌标准化为字符串格式的集合，用于比较"""
        normalized = set()
        for c in hand_cards:
            if isinstance(c, str):
                normalized.add(c)
            elif isinstance(c, list) and len(c) >= 2:
                normalized.add(f"{c[0]}{c[1]}")
        return normalized
    
    def _check_card_consistency(self, action_cards, cur_pos, my_pos):
        """检查出牌是否在初始手牌中"""
        if not action_cards:
            return None
        
        # 获取该玩家的初始手牌集合
        player_hand_set = self.all_players_hands_sets.get(cur_pos, set())
        if not player_hand_set:
            return None  # 如果没有该玩家的手牌信息，不检查
        
        # 解析牌面
        played_cards = []
        if isinstance(action_cards, list):
            for c in action_cards:
                if isinstance(c, str):
                    played_cards.append(c)
                elif isinstance(c, list) and len(c) >= 2:
                    played_cards.append(f"{c[0]}{c[1]}")
        elif isinstance(action_cards, str):
            # 尝试解析字符串格式
            try:
                import ast
                parsed = ast.literal_eval(action_cards)
                if isinstance(parsed, list) and len(parsed) > 2:
                    # 解析出牌列表
                    cards_data = parsed[2]
                    if isinstance(cards_data, list):
                        for c in cards_data:
                            if isinstance(c, str):
                                played_cards.append(c)
                            elif isinstance(c, list) and len(c) >= 2:
                                played_cards.append(f"{c[0]}{c[1]}")
            except:
                pass
        
        # 检查是否有牌不在初始手牌中
        missing_cards = []
        for card in played_cards:
            if card not in player_hand_set:
                missing_cards.append(card)
        
        if missing_cards:
            # 显示更多调试信息
            debug_info = f"（{cur_pos}号位初始手牌共{len(player_hand_set)}张，可能记录不完整）"
            return f"⚠ 数据不一致：出牌 {', '.join(missing_cards)} 不在{cur_pos}号位初始手牌中{debug_info}"
        
        return None
    
    def _calculate_remaining_cards(self, step: int) -> Dict[int, int]:
        """计算到指定步骤时每个玩家的剩余牌数"""
        cards = {0: 27, 1: 27, 2: 27, 3: 27}
        
        # 使用所有玩家的初始手牌信息
        all_hands = self.game_data.get('all_players_hands', {})
        if not all_hands:
            # 兼容旧格式
            my_pos = self.game_data['player_id']
            all_hands = {my_pos: self.game_data.get('initial_hand', [])}
        
        for pos, hand_cards in all_hands.items():
            if hand_cards:
                cards[pos] = len(hand_cards)
        
        # 遍历到当前步骤的所有动作，计算剩余牌数
        actions = self.game_data.get('actions', [])
        for i in range(min(step + 1, len(actions))):
            action = actions[i]
            cur_pos = action['cur_pos']
            cur_action = action['cur_action']
            
            # 解析cur_action
            if isinstance(cur_action, str):
                try:
                    import ast
                    cur_action = ast.literal_eval(cur_action)
                except:
                    continue
            
            if not cur_action or (isinstance(cur_action, list) and len(cur_action) == 0):
                continue
            
            if isinstance(cur_action, list) and cur_action[0] == "PASS":
                continue
            
            # 计算出的牌数
            if isinstance(cur_action, list) and len(cur_action) > 2:
                action_cards = cur_action[2]
                if action_cards:
                    if isinstance(action_cards, list):
                        card_count = len(action_cards)
                    elif isinstance(action_cards, str):
                        # 尝试解析字符串
                        try:
                            import ast
                            parsed = ast.literal_eval(action_cards)
                            card_count = len(parsed) if isinstance(parsed, list) else 1
                        except:
                            card_count = 1
                    else:
                        card_count = 1
                    
                    cards[cur_pos] = max(0, cards[cur_pos] - card_count)
        
        return cards
    
    def _calculate_remaining_hand_cards(self, step: int) -> Dict[int, list]:
        """计算到指定步骤时每个玩家的剩余手牌（实际牌面）"""
        # 复制初始手牌
        remaining_hands = {}
        for pos, hand_list in self.all_players_hands_lists.items():
            remaining_hands[pos] = hand_list.copy()
        
        # 遍历到当前步骤的所有动作，移除已打出的牌
        actions = self.game_data.get('actions', [])
        for i in range(min(step + 1, len(actions))):
            action = actions[i]
            cur_pos = action['cur_pos']
            cur_action = action['cur_action']
            
            # 解析cur_action
            if isinstance(cur_action, str):
                try:
                    import ast
                    cur_action = ast.literal_eval(cur_action)
                except:
                    continue
            
            if not cur_action or (isinstance(cur_action, list) and len(cur_action) == 0):
                continue
            
            if isinstance(cur_action, list) and cur_action[0] == "PASS":
                continue
            
            # 获取打出的牌
            if isinstance(cur_action, list) and len(cur_action) > 2:
                action_cards = cur_action[2]
                if action_cards and cur_pos in remaining_hands:
                    # 规范化打出的牌
                    played_cards = []
                    for c in action_cards:
                        if isinstance(c, str):
                            played_cards.append(c)
                        elif isinstance(c, list) and len(c) >= 2:
                            played_cards.append(f"{c[0]}{c[1]}")
                    
                    # 从剩余手牌中移除打出的牌
                    for card in played_cards:
                        if card in remaining_hands[cur_pos]:
                            remaining_hands[cur_pos].remove(card)
        
        return remaining_hands
    
    def _get_action_type_stats(self, step: int) -> Dict[str, int]:
        """统计到指定步骤时的牌型使用情况"""
        stats = {}
        actions = self.game_data.get('actions', [])
        
        for i in range(min(step + 1, len(actions))):
            action = actions[i]
            cur_action = action['cur_action']
            
            # 解析cur_action
            if isinstance(cur_action, str):
                try:
                    import ast
                    cur_action = ast.literal_eval(cur_action)
                except:
                    continue
            
            if not cur_action or (isinstance(cur_action, list) and len(cur_action) == 0):
                continue
            
            if isinstance(cur_action, list):
                action_type = cur_action[0] if len(cur_action) > 0 else "PASS"
                if action_type != "PASS":
                    stats[action_type] = stats.get(action_type, 0) + 1
        
        return stats
        
    def display_current_state(self):
        """显示当前游戏状态"""
        actions = self.game_data.get('actions', [])
        my_pos = self.game_data['player_id']
        teammate_pos = (my_pos + 2) % 4
        
        # 计算当前剩余牌数
        remaining_cards = self._calculate_remaining_cards(self.current_step)
        
        # 统计牌型使用情况
        action_stats = self._get_action_type_stats(self.current_step)
        
        # 清屏（简化版）
        print("\n" * 2)
        print("=" * 80)
        print(f"游戏回放: {self.game_data['game_id']}")
        print(f"玩家: {self.game_data['player_name']} (位置{my_pos})")
        print(f"进度: {self.current_step}/{len(actions)} 步")
        print("=" * 80)
        
        # 显示玩家剩余牌数
        print(f"\n【玩家剩余牌数】:")
        for pos in range(4):
            if pos == my_pos:
                label = "我"
            elif pos == teammate_pos:
                label = "队友"
            else:
                label = "对手"
            print(f"  {pos}号位({label}): {remaining_cards[pos]}张", end="  ")
        print()
        
        # 显示牌型统计
        if action_stats:
            print(f"\n【牌型统计】:")
            stats_str = "  "
            for action_type, count in sorted(action_stats.items()):
                stats_str += f"{action_type}:{count}  "
            print(stats_str)
        
        # 显示所有玩家的当前手牌（初始或剩余）
        my_pos = self.game_data['player_id']
        teammate_pos = (my_pos + 2) % 4
        
        # 获取当前剩余手牌
        if self.current_step == 0:
            # 第0步显示初始手牌
            all_hands = self.game_data.get('all_players_hands', {})
            if not all_hands:
                # 兼容旧格式
                all_hands = {my_pos: self.game_data.get('initial_hand', [])}
            
            # 规范化键为整数
            normalized_hands = {}
            for pos, hand_cards in all_hands.items():
                if isinstance(pos, str):
                    try:
                        pos = int(pos)
                    except:
                        continue
                normalized_hands[pos] = hand_cards
            all_hands = normalized_hands
            title = "【所有玩家初始手牌】"
        else:
            # 其他步骤显示剩余手牌
            remaining_hands = self._calculate_remaining_hand_cards(self.current_step)
            all_hands = remaining_hands
            title = "【所有玩家剩余手牌】"
        
        print(f"\n{title}:")
        print("-" * 80)
        
        from collections import Counter
        
        # 牌点大小顺序
        rank_order = {'3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6, '9': 7, 
                     'T': 8, 'J': 9, 'Q': 10, 'K': 11, 'A': 12, '2': 13, 
                     'B': 14, 'R': 15}
        
        # 花色顺序（同牌点时按此顺序）
        suit_order = {'C': 1, 'D': 2, 'H': 3, 'S': 4, 'B': 5, 'R': 6}
        
        suits = {'H': '红桃', 'S': '黑桃', 'C': '梅花', 'D': '方块', 'B': '小王', 'R': '大王'}
        
        # 按牌点大小排序，同牌点按花色排序
        def card_sort_key(card):
            if len(card) < 2:
                return (999, 999)
            suit = card[0]
            rank = card[1]
            rank_val = rank_order.get(rank, 999)
            suit_val = suit_order.get(suit, 999)
            return (rank_val, suit_val)
        
        def format_hand(hand_cards):
            """格式化手牌显示"""
            if not hand_cards:
                return "已出完"
            
            # 处理不同格式的手牌
            normalized_cards = []
            for c in hand_cards:
                if isinstance(c, str):
                    normalized_cards.append(c)
                elif isinstance(c, list) and len(c) >= 2:
                    normalized_cards.append(f"{c[0]}{c[1]}")
                else:
                    normalized_cards.append(str(c))
            
            card_counts = Counter(normalized_cards)
            hand_display = []
            for card in sorted(card_counts.keys(), key=card_sort_key):
                count = card_counts[card]
                suit = card[0] if len(card) > 0 else ''
                rank = card[1] if len(card) > 1 else ''
                suit_name = suits.get(suit, suit)
                if count > 1:
                    hand_display.append(f"{suit_name}{rank}({count})")
                else:
                    hand_display.append(f"{suit_name}{rank}")
            return ' '.join(hand_display)
        
        # 显示每个玩家的手牌
        for pos in range(4):
            if pos == my_pos:
                label = "我"
            elif pos == teammate_pos:
                label = "队友"
            else:
                label = "对手"
            
            hand_cards = all_hands.get(pos, [])
            total_count = len(hand_cards) if hand_cards else 0
            hand_display = format_hand(hand_cards)
            print(f"  {pos}号位({label}): {total_count}张 - {hand_display}")
        
        # 显示当前步骤及之前的步骤
        print(f"\n【出牌过程】:")
        print("-" * 80)
        
        for i in range(min(self.current_step + 1, len(actions))):
            action = actions[i]
            cur_pos = action['cur_pos']
            cur_action = action['cur_action']
            greater_pos = action['greater_pos']
            greater_action = action['greater_action']
            
            # 如果cur_action是字符串，尝试解析为列表
            if isinstance(cur_action, str):
                try:
                    import ast
                    cur_action = ast.literal_eval(cur_action)
                except:
                    pass
            
            if not cur_action or (isinstance(cur_action, list) and len(cur_action) == 0) or (isinstance(cur_action, list) and cur_action[0] == "PASS"):
                continue
            
            # 判断玩家关系
            if cur_pos == my_pos:
                player_label = "我"
                marker = ">>>"
            elif cur_pos == teammate_pos:
                player_label = "队友"
                marker = "   "
            else:
                player_label = "对手"
                marker = "   "
            
            # 格式化显示
            if isinstance(cur_action, list):
                action_type = cur_action[0] if len(cur_action) > 0 else "PASS"
                action_rank = cur_action[1] if len(cur_action) > 1 else ""
                action_cards = cur_action[2] if len(cur_action) > 2 else []
            else:
                action_type = str(cur_action)
                action_rank = ""
                action_cards = []
            
            cards_str = _format_cards(action_cards)
            
            # 如果action_rank有值，也显示出来
            rank_str = f" {action_rank}" if action_rank else ""
            
            # 检查数据一致性（仅检查我方的出牌）
            consistency_warning = self._check_card_consistency(action_cards, cur_pos, my_pos)
            
            # 高亮当前步骤
            if i == self.current_step:
                # 分析规则使用情况
                rule_info = self._analyze_step(i, action, my_pos, teammate_pos)
                print(f"{marker} {i+1:3d}. [{player_label:2s}] {cur_pos}号位: {action_type}{rank_str} {cards_str} ← 当前")
                if rule_info:
                    print(f"       {rule_info}")
                if consistency_warning:
                    print(f"       {consistency_warning}")
            else:
                line = f"    {i+1:3d}. [{player_label:2s}] {cur_pos}号位: {action_type}{rank_str} {cards_str}"
                if consistency_warning:
                    line += f" {consistency_warning}"
                print(line)
        
        # 显示控制提示
        print("\n" + "-" * 80)
        print("控制: [1]自动回放  [2]停止  [3]下一步  [4]上一步  [q]退出")
        if self.auto_play:
            print(f"⏩ 自动播放中... (速度: {self.auto_speed:.1f}秒/步)")
        print("-" * 80)
    
    def next_step(self):
        """下一步"""
        actions = self.game_data.get('actions', [])
        if self.current_step < len(actions) - 1:
            self.current_step += 1
            return True
        return False
    
    def prev_step(self):
        """上一步"""
        if self.current_step > 0:
            self.current_step -= 1
            return True
        return False
    
    def start_auto_play(self):
        """开始自动播放"""
        self.auto_play = True
    
    def stop_auto_play(self):
        """停止自动播放"""
        self.auto_play = False
    
    def _analyze_step(self, step: int, action: Dict, my_pos: int, teammate_pos: int) -> str:
        """分析当前步骤的规则使用情况"""
        cur_pos = action['cur_pos']
        cur_action = action['cur_action']
        greater_pos = action['greater_pos']
        
        # 只分析我方的决策
        if cur_pos != my_pos:
            return ""
        
        if not cur_action or len(cur_action) == 0 or cur_action[0] == "PASS":
            return ""
        
        action_type = cur_action[0]
        violations = []
        
        # 规则1: 队友控场时不应该用炸弹压队友
        if greater_pos == teammate_pos and action_type == "Bomb":
            violations.append("⚠ 用炸弹压队友（违反队友保护规则）")
        
        # 规则2: 开局阶段不应该越级打大牌
        if step < 20:  # 前20步算开局
            if action_type == "Single" and len(cur_action) > 1:
                rank = cur_action[1]
                # 检查前一步的牌值
                if step > 0:
                    prev_action = self.game_data['actions'][step - 1]
                    if prev_action.get('cur_action') and len(prev_action['cur_action']) > 1:
                        prev_rank = prev_action['cur_action'][1]
                        rank_values = {'3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, 
                                      '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 
                                      'A': 14, '2': 15, 'B': 16, 'R': 17}
                        if rank in rank_values and prev_rank in rank_values:
                            if rank_values[rank] - rank_values[prev_rank] > 5:
                                violations.append(f"⚠ 越级打大牌（从{prev_rank}跳到{rank}）")
        
        return " | ".join(violations) if violations else ""
    
    def run(self):
        """运行交互式回放"""
        import os
        
        while True:
            # 清屏
            os.system('cls' if os.name == 'nt' else 'clear')
            
            self.display_current_state()
            
            if self.auto_play:
                # 自动播放模式
                time.sleep(self.auto_speed)
                if not self.next_step():
                    self.stop_auto_play()
                    print("\n⏹ 已播放到末尾，自动停止")
                    time.sleep(2)
            else:
                # 手动控制模式
                print("\n请选择操作:")
                print("  [1] 自动回放")
                print("  [2] 停止")
                print("  [3] 下一步")
                print("  [4] 上一步")
                print("  [q] 退出")
                
                try:
                    key = input("\n请输入: ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                
                if key == '1':
                    self.start_auto_play()
                elif key == '2':
                    self.stop_auto_play()
                elif key == '3':
                    if not self.next_step():
                        print("\n⚠ 已到末尾")
                        time.sleep(1)
                elif key == '4':
                    if not self.prev_step():
                        print("\n⚠ 已到开头")
                        time.sleep(1)
                elif key == 'q' or key == 'Q':
                    break
                elif key == '':
                    # 回车键，默认下一步
                    if not self.next_step():
                        print("\n⚠ 已到末尾")
                        time.sleep(1)


def replay_interactive(filepath: Path):
    """交互式回放游戏"""
    if not filepath.exists():
        print(f"文件不存在: {filepath}")
        return
    
    game_data = GameRecorder.load_game(filepath)
    replay = InteractiveReplay(game_data)
    replay.run()


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法:")
        print("  python replay_game_interactive.py <game_file>  # 交互式回放")
        print("  python replay_game_interactive.py --list       # 列出所有游戏记录")
        return
    
    if sys.argv[1] == "--list":
        from communication.replay_game import list_games
        games = list_games()
        print(f"\n找到 {len(games)} 个游戏记录:\n")
        for i, game_file in enumerate(games[:20], 1):
            print(f"{i}. {game_file.name}")
        return
    
    # 交互式回放
    filepath = Path(sys.argv[1])
    if not filepath.is_absolute():
        record_dir = Path(__file__).parent.parent.parent / "game_records_v7"
        filepath = record_dir / sys.argv[1]
    
    replay_interactive(filepath)


if __name__ == "__main__":
    main()

