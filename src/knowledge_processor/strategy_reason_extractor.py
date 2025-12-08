# -*- coding: utf-8 -*-
"""
策略原因提取器
根据策略类型和游戏状态，提取策略选择的原因
"""
from typing import Dict, List, Optional, Tuple


def extract_strategy_reason(
    state_dict: Dict,
    action_cards: List,
    strategy_type: str,
    last_action: Optional[Dict] = None
) -> Dict[str, str]:
    """
    提取策略原因
    
    Args:
        state_dict: 状态字典，包含手牌、历史、玩家信息等
        action_cards: 动作卡牌列表
        strategy_type: 策略类型（bomb, suppress, protect, control, group, follow, discard）
        last_action: 上一步动作
    
    Returns:
        {
            'reason_type': 原因类型（与策略类型对应）
            'reason_description': 原因描述（详细说明为什么选择这个策略）
        }
    """
    if not action_cards or strategy_type == 'unknown':
        return {
            'reason_type': 'unknown',
            'reason_description': '无法识别策略原因'
        }
    
    action_type = state_dict.get('action_type', '')
    player_rest_cards = state_dict.get('player_rest_cards', [27, 27, 27, 27])
    current_player = state_dict.get('current_player', 0)
    game_phase = state_dict.get('game_phase', 1)  # 0=开局, 1=中局, 2=残局
    
    # 计算队友和对手
    teammate = (current_player + 2) % 4
    opponents = [i for i in range(4) if i != current_player and i != teammate]
    
    # 获取对手和队友的剩余牌数
    opponent_rest_cards = [player_rest_cards[i] for i in opponents if i < len(player_rest_cards)]
    teammate_rest_cards = player_rest_cards[teammate] if teammate < len(player_rest_cards) else 27
    min_opponent_cards = min(opponent_rest_cards) if opponent_rest_cards else 27
    max_opponent_cards = max(opponent_rest_cards) if opponent_rest_cards else 27
    current_player_cards = player_rest_cards[current_player] if current_player < len(player_rest_cards) else 27
    
    # 根据策略类型提取原因
    if strategy_type == 'bomb':
        # 出炸弹的原因
        if min_opponent_cards <= 5:
            return {
                'reason_type': 'bomb_urgent',
                'reason_description': f'对手快走完（剩余{min_opponent_cards}张），使用炸弹阻止对手冲刺'
            }
        elif game_phase == 2:  # 残局
            return {
                'reason_type': 'bomb_endgame',
                'reason_description': '残局阶段，使用炸弹夺取牌权，争取上游'
            }
        elif last_action and last_action.get('type') not in ['PASS', None, '']:
            return {
                'reason_type': 'bomb_counter',
                'reason_description': f'使用炸弹压制上一步{last_action.get("type")}，夺取牌权'
            }
        else:
            return {
                'reason_type': 'bomb_opportunity',
                'reason_description': '关键时机，使用炸弹夺取牌权'
            }
    
    elif strategy_type == 'suppress':
        # 压制对手的原因
        if min_opponent_cards <= 8:
            if len(action_cards) >= 4:
                return {
                    'reason_type': 'suppress_urgent',
                    'reason_description': f'对手快走完（剩余{min_opponent_cards}张），使用大牌压制对手，阻止其冲刺'
                }
            elif action_type in ['Pair', 'Trips', 'ThreeWithTwo', 'Straight']:
                return {
                    'reason_type': 'suppress_combo',
                    'reason_description': f'对手快走完，使用{action_type}压制对手，阻止其行动'
                }
        if last_action:
            last_action_player = None
            history = state_dict.get('history', [])
            if history:
                last_history = history[-1]
                last_action_player = last_history.get('player')
            if last_action_player is not None and last_action_player in opponents:
                return {
                    'reason_type': 'suppress_block',
                    'reason_description': f'对手传牌，及时阻截，防止对手配合'
                }
        return {
            'reason_type': 'suppress_general',
            'reason_description': '主动压制对手，阻止对手行动'
        }
    
    elif strategy_type == 'protect':
        # 保护队友的原因
        if teammate_rest_cards <= 10:
            if last_action:
                last_action_player = None
                history = state_dict.get('history', [])
                if history:
                    last_history = history[-1]
                    last_action_player = last_history.get('player')
                if last_action_player is not None and last_action_player in opponents:
                    return {
                        'reason_type': 'protect_teammate_urgent',
                        'reason_description': f'队友快走完（剩余{teammate_rest_cards}张），阻止对手传牌，保护队友冲刺'
                    }
            return {
                'reason_type': 'protect_teammate',
                'reason_description': f'队友快走完（剩余{teammate_rest_cards}张），使用大牌保护队友'
            }
        elif min_opponent_cards > 0 and teammate_rest_cards <= min_opponent_cards - 5:
            return {
                'reason_type': 'protect_advantage',
                'reason_description': f'队友牌数明显少于对手（队友{teammate_rest_cards}张 vs 对手{min_opponent_cards}张），保护队友优势'
            }
        else:
            return {
                'reason_type': 'protect_general',
                'reason_description': '保护队友，防止对手干扰'
            }
    
    elif strategy_type == 'control':
        # 控牌的原因
        if min_opponent_cards <= 8:
            return {
                'reason_type': 'control_urgent',
                'reason_description': f'对手快走完（剩余{min_opponent_cards}张），控制节奏，防止对手冲刺'
            }
        elif game_phase == 2:  # 残局
            return {
                'reason_type': 'control_endgame',
                'reason_description': '残局阶段，控制出牌节奏，等待最佳时机'
            }
        else:
            return {
                'reason_type': 'control_general',
                'reason_description': '控制节奏，掌握主动权'
            }
    
    elif strategy_type == 'group':
        # 组牌的原因
        hand_cards = state_dict.get('hand', [])
        remaining_cards = len(hand_cards) - len(action_cards)
        
        # 判断是否减少了手数
        if action_type in ['ThreeWithTwo', 'ThreePair', 'TwoTrips']:
            return {
                'reason_type': 'group_reduce_hands',
                'reason_description': f'使用{action_type}减少手数，从{len(hand_cards)}张减少到{remaining_cards}张'
            }
        elif action_type in ['Pair', 'Trips']:
            return {
                'reason_type': 'group_reduce_singles',
                'reason_description': f'使用{action_type}减少单牌，优化牌型结构'
            }
        elif action_type == 'Straight':
            return {
                'reason_type': 'group_optimize',
                'reason_description': f'使用顺子优化牌型，减少手牌数量'
            }
        else:
            return {
                'reason_type': 'group_general',
                'reason_description': '减少手数，优化牌型'
            }
    
    elif strategy_type == 'follow':
        # 跟牌的原因
        if last_action:
            last_action_type = last_action.get('type', '')
            if last_action_type in ['Pair', 'Trips', 'ThreeWithTwo', 'Straight']:
                return {
                    'reason_type': 'follow_counter',
                    'reason_description': f'压制上一步{last_action_type}，夺取牌权'
                }
            elif last_action_type in ['Single']:
                return {
                    'reason_type': 'follow_single',
                    'reason_description': '压制上一步单牌，夺取牌权'
                }
            else:
                return {
                    'reason_type': 'follow_general',
                    'reason_description': f'跟牌压制上一步{last_action_type}，保持主动权'
                }
        else:
            return {
                'reason_type': 'follow_general',
                'reason_description': '跟牌，保持主动权'
            }
    
    elif strategy_type == 'discard':
        # 顺牌/出牌的原因
        if game_phase == 0:  # 开局
            return {
                'reason_type': 'discard_opening',
                'reason_description': '开局阶段，顺牌出牌，等待机会'
            }
        elif game_phase == 2:  # 残局
            if current_player_cards <= 5:
                return {
                    'reason_type': 'discard_endgame',
                    'reason_description': f'残局阶段，剩余{current_player_cards}张，顺牌出牌，争取上游'
                }
            else:
                return {
                    'reason_type': 'discard_endgame',
                    'reason_description': '残局阶段，顺牌出牌，等待机会'
                }
        else:
            return {
                'reason_type': 'discard_general',
                'reason_description': '顺牌出牌，减少手牌，等待机会'
            }
    
    else:
        return {
            'reason_type': 'unknown',
            'reason_description': '无法识别策略原因'
        }

