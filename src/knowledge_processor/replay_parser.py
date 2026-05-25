# -*- coding: utf-8 -*-
import json
import os
import ast
import sys
import io
from typing import List, Dict, Tuple
import numpy as np

# **修复**：设置Windows控制台编码为UTF-8
try:
    from src.utils.encoding_fix import fix_windows_console_encoding
    fix_windows_console_encoding()
except ImportError:
    # 如果导入失败，使用备用方案
    if sys.platform == 'win32':
        try:
            import io
            # 检查并修复stdout编码
            if hasattr(sys.stdout, 'buffer'):
                # 如果已经是TextIOWrapper但编码不是utf-8，需要重新包装
                if isinstance(sys.stdout, io.TextIOWrapper):
                    current_encoding = getattr(sys.stdout, 'encoding', None)
                    if current_encoding and current_encoding.lower() not in ('utf-8', 'utf8'):
                        # 保存原始buffer，重新包装为UTF-8
                        original_buffer = sys.stdout.buffer
                        sys.stdout = io.TextIOWrapper(original_buffer, encoding='utf-8', errors='replace')
                else:
                    # 如果不是TextIOWrapper，直接包装
                    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            
            # 检查并修复stderr编码
            if hasattr(sys.stderr, 'buffer'):
                if isinstance(sys.stderr, io.TextIOWrapper):
                    current_encoding = getattr(sys.stderr, 'encoding', None)
                    if current_encoding and current_encoding.lower() not in ('utf-8', 'utf8'):
                        original_buffer = sys.stderr.buffer
                        sys.stderr = io.TextIOWrapper(original_buffer, encoding='utf-8', errors='replace')
                else:
                    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        except (AttributeError, ValueError, OSError, TypeError):
            # 如果设置失败，继续执行（可能是文件操作冲突或其他原因）
            pass

# 直接定义策略类型识别函数，避免循环导入
def identify_strategy_type(state_dict, action_cards, last_action=None):
    """简化版策略类型识别（避免循环导入）"""
    if not action_cards:
        return 'unknown'

    action_type = state_dict.get('action_type', '')
    player_rest_cards = state_dict.get('player_rest_cards', [27, 27, 27, 27])
    current_player = state_dict.get('current_player', 0)

    # 计算队友和对手
    teammate = (current_player + 2) % 4
    opponents = [i for i in range(4) if i != current_player and i != teammate]

    # 获取对手和队友的剩余牌数
    opponent_rest_cards = [player_rest_cards[i] for i in opponents if i < len(player_rest_cards)]
    teammate_rest_cards = player_rest_cards[teammate] if teammate < len(player_rest_cards) else 27
    min_opponent_cards = min(opponent_rest_cards) if opponent_rest_cards else 27

    # 1. 判断是否是出炸弹（优先级最高）
    if action_type in ['Bomb', 'BOMB']:
        return 'bomb'

    # 2. 判断是否是保护队友
    if last_action:
        history = state_dict.get('history', [])
        if history:
            last_history = history[-1]
            last_action_player = last_history.get('player')
            if last_action_player is not None and last_action_player in opponents:
                if action_type == last_action.get('type') and action_type not in ['PASS', '']:
                    # 如果队友快走完（剩余牌数<=10），优先识别为保护队友
                    if teammate_rest_cards <= 10:
                        return 'protect'
                    # 如果队友牌数明显少于对手（队友牌数 <= 对手最小牌数-5），也可能是保护队友
                    elif min_opponent_cards > 0 and teammate_rest_cards <= min_opponent_cards - 5:
                        return 'protect'
                    # 否则识别为压制对手
                    else:
                        return 'suppress'

    # 额外判断：如果队友快走完且对手也快走完，使用大牌可能是保护队友
    if teammate_rest_cards <= 10 and min_opponent_cards <= 10:
        # 如果出牌数量多（>=4），可能是保护队友
        if len(action_cards) >= 4 and action_type not in ['Bomb', 'BOMB']:
            return 'protect'

    # 3. 判断是否是压制对手
    if min_opponent_cards <= 8:
        # 如果出牌数量多（>=4），且不是炸弹，可能是压制
        if len(action_cards) >= 4 and action_type not in ['Bomb', 'BOMB']:
            return 'suppress'
        # 如果是对子、三带二等组合牌型，且对手快走完，可能是压制
        if action_type in ['Pair', 'Trips', 'ThreeWithTwo', 'Straight']:
            return 'suppress'

    # 4. 判断控牌
    if min_opponent_cards <= 8:
        # 如果出牌数量多，且不是组合牌型，可能是控牌
        if len(action_cards) >= 4 and action_type not in ['Pair', 'Trips', 'ThreeWithTwo', 'Straight']:
            return 'control'

    # 5. 判断跟牌
    if last_action and last_action.get('type') not in ['PASS', None, '']:
        if action_type == last_action.get('type') and action_type not in ['PASS', '']:
            return 'follow'

    # 6. 判断组牌
    if action_type in ['Pair', 'Trips', 'ThreeWithTwo', 'Straight', 'ThreePair', 'TwoTrips']:
        return 'group'

    # 7. 其他情况：顺牌/出牌
    return 'discard'

class ReplayParser:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        
    def load_replays(self) -> List[Dict]:
        """Load all JSON replay files from the directory."""
        replays = []
        if not os.path.exists(self.data_dir):
            print(f"Warning: Directory {self.data_dir} does not exist.")
            return []
            
        for filename in os.listdir(self.data_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.data_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        replays.append(data)
                except Exception as e:
                    print(f"Error loading {filename}: {e}")
        return replays

    def parse_action_string(self, action_str) -> Tuple[str, List[str]]:
        """
        Parse action string or list like "['Straight', '6', ['C6', 'S7', 'S8', 'S9', 'HT']]"
        or ['Single', '4', ['H4']]
        Returns (Type, CardList)
        """
        # 如果已经是列表格式，直接处理
        if isinstance(action_str, list):
            if len(action_str) >= 1:
                if action_str[0] == 'PASS':
                    return 'PASS', []
                # 格式: [type, rank, cards] 或 [type, cards]
                if len(action_str) >= 3 and isinstance(action_str[2], list):
                    return action_str[0], action_str[2]
                elif len(action_str) >= 2 and isinstance(action_str[1], list):
                    return action_str[0], action_str[1]
                else:
                    return action_str[0], []
            return 'UNKNOWN', []
        
        # 如果是字符串格式，尝试解析
        if isinstance(action_str, str):
            try:
                # Use ast.literal_eval to safely parse the string representation of list
                parsed = ast.literal_eval(action_str)
                if isinstance(parsed, list) and len(parsed) >= 1:
                    if parsed[0] == 'PASS':
                        return 'PASS', []
                    if len(parsed) >= 3 and isinstance(parsed[2], list):
                        return parsed[0], parsed[2]
                    elif len(parsed) >= 2 and isinstance(parsed[1], list):
                        return parsed[0], parsed[1]
                    else:
                        return parsed[0], []
            except:
                # Handle potential format variations
                if 'PASS' in action_str:
                    return 'PASS', []
                return 'UNKNOWN', []
        
        return 'UNKNOWN', []

    def extract_training_data(self, replays: List[Dict]):
        """
        完善版：提取完整的训练数据，包含所有必要的状态信息
        
        基于阶段0的分析，添加了以下缺失的状态信息：
        - last_action: 上一步动作
        - action_type: 当前动作类型
        - game_phase: 游戏阶段
        - cur_rank: 当前级牌
        - current_player: 当前玩家
        - hands: 所有玩家的手牌
        - player_rest_cards: 玩家剩余牌数
        """
        dataset = []
        
        for replay in replays:
            # 获取Hero信息
            hero_id = replay.get('player_id')
            hero_hand = set(replay.get('initial_hand', []))
            
            # 获取所有玩家的手牌信息
            all_hands_raw = replay.get('all_players_hands', {})
            all_hands = {}
            if isinstance(all_hands_raw, dict):
                for key, value in all_hands_raw.items():
                    # 键可能是字符串或整数
                    pos = int(key) if isinstance(key, str) and key.isdigit() else key
                    all_hands[pos] = value if isinstance(value, list) else list(value)
            else:
                # 如果没有all_players_hands，从initial_hand构建
                all_hands[hero_id] = list(hero_hand)
                for pos in range(4):
                    if pos != hero_id and pos not in all_hands:
                        all_hands[pos] = []  # 初始化为空，后续会更新
            
            # 获取游戏信息
            game_info = replay.get('game_info', {})
            cur_rank = game_info.get('curRank', '2')
            if not cur_rank:
                cur_rank = '2'  # 默认值
            
            # 初始化历史记录
            history = []
            
            for action_log in replay.get('actions', []):
                actor_pos = action_log['cur_pos']
                action_str = action_log['cur_action']
                action_type, cards_played = self.parse_action_string(action_str)
                
                # 如果是Hero的回合，记录完整的状态信息
                if actor_pos == hero_id:
                    # 计算玩家剩余牌数
                    player_rest_cards = []
                    for pos in range(4):
                        if pos in all_hands and isinstance(all_hands[pos], list):
                            player_rest_cards.append(len(all_hands[pos]))
                        else:
                            # 估算剩余牌数（简化：从初始手牌减去已出的牌）
                            player_rest_cards.append(27)
                    
                    # 确定游戏阶段（根据已出牌数）
                    total_cards_played = sum([27 - rest for rest in player_rest_cards])
                    if total_cards_played < 20:
                        game_phase = 0  # opening
                    elif total_cards_played < 80:
                        game_phase = 1  # mid
                    else:
                        game_phase = 2  # endgame
                    
                    # 获取上一步动作
                    last_action = {}
                    if history:
                        last_history = history[-1]
                        last_action_str = last_history.get('action_str', '')
                        if last_action_str:
                            last_action_type, last_action_cards = self.parse_action_string(last_action_str)
                            last_action = {
                                'type': last_action_type,
                                'cards': last_action_cards
                            }
                    
                    # 构建完整状态字典（包含所有必要信息）
                    state = {
                        'hand': list(hero_hand),
                        'history': history[-10:],  # Last 10 moves
                        'current_player': hero_id,
                        'hands': all_hands,
                        'last_action': last_action,
                        'action_type': action_type,
                        'game_phase': game_phase,
                        'cur_rank': cur_rank,
                        'player_rest_cards': player_rest_cards
                    }
                    
                    # 识别策略类型
                    strategy_type = identify_strategy_type(
                        state_dict=state,
                        action_cards=cards_played,
                        last_action=last_action if last_action else None
                    )
                    
                    # 将策略类型添加到状态中
                    state['strategy_type'] = strategy_type
                    
                    # 提取策略原因
                    try:
                        from src.knowledge_processor.strategy_reason_extractor import extract_strategy_reason
                        strategy_reason = extract_strategy_reason(
                            state_dict=state,
                            action_cards=cards_played,
                            strategy_type=strategy_type,
                            last_action=last_action if last_action else None
                        )
                        state['strategy_reason'] = strategy_reason
                    except ImportError:
                        # 如果导入失败，使用默认值
                        state['strategy_reason'] = {
                            'reason_type': 'unknown',
                            'reason_description': '无法提取策略原因'
                        }
                    
                    # 评估策略效果
                    try:
                        from src.knowledge_processor.strategy_encoder import StrategyEncoder
                        # 初始化策略编码器（如果还没有初始化）
                        if not hasattr(self, '_strategy_encoder'):
                            self._strategy_encoder = StrategyEncoder()
                        
                        # 将game_phase从数字转换为字符串
                        game_phase_str = ['opening', 'mid', 'endgame'][game_phase] if game_phase in [0, 1, 2] else 'mid'
                        
                        # 计算策略效果分数
                        effectiveness_score = self._strategy_encoder.calculate_shaping_reward(
                            state_dict=state,
                            action_cards=cards_played,
                            action_type=action_type,
                            game_phase=game_phase_str,
                            cur_rank=cur_rank
                        )
                        state['strategy_effectiveness'] = effectiveness_score
                    except (ImportError, AttributeError, KeyError, IndexError) as e:
                        # 如果导入失败或计算出错，使用默认值
                        state['strategy_effectiveness'] = 0.0
                    
                    # **新增**：标注6个策略学习任务
                    strategy_labels = self._annotate_strategy_tasks(
                        state_dict=state,
                        action_cards=cards_played,
                        action_type=action_type,
                        game_phase=game_phase,
                        hand_cards=hero_hand,
                        last_action=last_action
                    )
                    state['strategy_tasks'] = strategy_labels
                    
                    # Target Action
                    target = cards_played
                    
                    dataset.append((state, target))
                    
                    # Update Hero's hand
                    for card in cards_played:
                        if card in hero_hand:
                            hero_hand.remove(card)
                    
                    # 更新all_hands中Hero的手牌
                    if hero_id in all_hands:
                        all_hands[hero_id] = list(hero_hand)
                
                # Update History（保存action_str以便后续提取last_action）
                history.append({
                    'player': actor_pos,
                    'action': cards_played,
                    'action_str': action_str,  # 保存原始action_str
                    'action_type': action_type
                })
                
                # 更新all_hands中对应玩家的手牌（如果知道的话）
                # 注意：这里只能更新Hero的手牌，其他玩家的手牌需要从replay数据中获取
                if actor_pos in all_hands and isinstance(all_hands[actor_pos], list):
                    # 从手牌中移除已出的牌
                    for card in cards_played:
                        if card in all_hands[actor_pos]:
                            all_hands[actor_pos].remove(card)
                
        return dataset
    
    def _annotate_strategy_tasks(self, state_dict: Dict, action_cards: List[str], 
                                 action_type: str, game_phase: int, 
                                 hand_cards: List[str], last_action: Dict = None) -> Dict:
        """
        标注6个策略学习任务
        
        返回:
            {
                'grouping': int,          # 0-6: 不组牌/组对子/组三张/组三带二/组顺子/组钢板/组木板
                'role': int,              # 0-2: 主攻/助攻/平衡
                'power': float,           # 0-10: 牌力分数
                'protect_suppress': int,  # 0-2: 保护队友/压制对手/无
                'bomb_timing': int,       # 0-4: 开局/中期/残局/关键压制/不出
                'red_heart': int          # 0-3: 组牌/炸弹/保留/不使用
            }
        """
        try:
            from src.decision.card_power_evaluator import calculate_card_power
            
            # 任务1: 组牌策略分类
            grouping_label = self._annotate_grouping_strategy(action_cards, action_type, hand_cards)
            
            # 任务2: 角色判断（基于牌力）
            game_phase_str = ['opening', 'mid', 'endgame'][game_phase] if game_phase in [0, 1, 2] else 'mid'
            power_result = calculate_card_power(hand_cards, game_phase=game_phase_str)
            power_score = power_result.get('total_power', 5.0)
            role_label = 0 if power_score >= 7 else (1 if power_score < 5 else 2)  # 主攻/助攻/平衡
            
            # 任务3: 牌力评估（归一化到0-10）
            normalized_power = min(max(power_score / 2.0, 0.0), 10.0)  # 假设最大牌力约20
            
            # 任务4: 保护/压制判断
            protect_suppress_label = self._annotate_protect_suppress(
                state_dict, action_cards, action_type, last_action
            )
            
            # 任务5: 炸弹出炸时机
            bomb_timing_label = self._annotate_bomb_timing(
                action_type, game_phase, state_dict, action_cards
            )
            
            # 任务6: 红心配策略
            red_heart_label = self._annotate_red_heart_strategy(
                action_cards, action_type, hand_cards
            )
            
            return {
                'grouping': grouping_label,
                'role': role_label,
                'power': normalized_power,
                'protect_suppress': protect_suppress_label,
                'bomb_timing': bomb_timing_label,
                'red_heart': red_heart_label
            }
        except Exception as e:
            # 如果标注失败，返回默认值
            return {
                'grouping': 0,  # 不组牌
                'role': 2,      # 平衡
                'power': 5.0,   # 中等牌力
                'protect_suppress': 2,  # 无
                'bomb_timing': 4,  # 不出
                'red_heart': 3  # 不使用
            }
    
    def _annotate_grouping_strategy(self, action_cards: List[str], action_type: str, hand_cards: List[str]) -> int:
        """标注组牌策略：0=不组牌, 1=组对子, 2=组三张, 3=组三带二, 4=组顺子, 5=组钢板, 6=组木板"""
        if action_type == 'PASS':
            return 0  # 不组牌
        
        # 根据action_type判断
        type_map = {
            'Pair': 1,              # 组对子
            'Trips': 2,             # 组三张
            'ThreeWithTwo': 3,      # 组三带二
            'Straight': 4,          # 组顺子
            'TwoTrips': 5,          # 组钢板
            'ThreePair': 6,         # 组木板
            'Single': 0,            # 不组牌（单张）
            'Bomb': 0               # 不组牌（炸弹）
        }
        return type_map.get(action_type, 0)
    
    def _annotate_protect_suppress(self, state_dict: Dict, action_cards: List[str], 
                                   action_type: str, last_action: Dict) -> int:
        """标注保护/压制：0=保护队友, 1=压制对手, 2=无"""
        if action_type == 'PASS':
            return 2  # 无
        
        # 检查是否是保护队友（队友刚出牌，自己PASS或跟牌）
        strategy_type = state_dict.get('strategy_type', 'unknown')
        if strategy_type == 'protect':
            return 0  # 保护队友
        elif strategy_type == 'suppress':
            return 1  # 压制对手
        
        # 默认：无特殊意图
        return 2
    
    def _annotate_bomb_timing(self, action_type: str, game_phase: int, 
                             state_dict: Dict, action_cards: List[str]) -> int:
        """标注炸弹出炸时机：0=开局, 1=中期, 2=残局, 3=关键压制, 4=不出"""
        if action_type != 'Bomb':
            return 4  # 不出
        
        # 根据游戏阶段判断
        if game_phase == 0:  # 开局
            return 0
        elif game_phase == 1:  # 中期
            return 1
        elif game_phase == 2:  # 残局
            return 2
        
        # 检查是否是关键压制
        strategy_type = state_dict.get('strategy_type', 'unknown')
        if strategy_type == 'suppress' and len(action_cards) >= 4:
            return 3  # 关键压制
        
        return 1  # 默认：中期
    
    def _annotate_red_heart_strategy(self, action_cards: List[str], action_type: str, hand_cards: List[str]) -> int:
        """标注红心配策略：0=组牌, 1=炸弹, 2=保留, 3=不使用"""
        # 检查action_cards中是否包含红心配（HR）
        has_red_heart_in_action = any('HR' in card or card == 'HR' for card in action_cards)
        
        if not has_red_heart_in_action:
            # 检查手牌中是否有红心配但未使用
            has_red_heart_in_hand = any('HR' in card or card == 'HR' for card in hand_cards)
            if has_red_heart_in_hand:
                return 2  # 保留
            else:
                return 3  # 不使用
        
        # 如果使用了红心配，判断用途
        if action_type == 'Bomb':
            return 1  # 炸弹
        elif action_type in ['Pair', 'Trips', 'ThreeWithTwo', 'Straight', 'TwoTrips', 'ThreePair']:
            return 0  # 组牌
        else:
            return 0  # 默认：组牌

if __name__ == "__main__":
    # 测试脚本
    parser = ReplayParser("game_records")
    replays = parser.load_replays()
    print(f"加载了 {len(replays)} 个replay文件")
    
    data = parser.extract_training_data(replays)
    print(f"提取了 {len(data)} 个训练样本")
    
    if len(data) > 0:
        sample_state, sample_action = data[0]
        print(f"\n第一个样本:")
        print(f"  状态字段: {list(sample_state.keys())}")
        print(f"  策略类型: {sample_state.get('strategy_type', 'N/A')}")
        print(f"  动作类型: {sample_state.get('action_type', 'N/A')}")
        print(f"  手牌数量: {len(sample_state.get('hand', []))}")
        print(f"  动作卡牌: {sample_action[:5] if len(sample_action) > 5 else sample_action}...")
