# -*- coding: utf-8 -*-
"""
策略类型分析评估脚本
评估模型是否学会了不同策略类型
"""

import sys
import os
import torch
import numpy as np
import json
from datetime import datetime
from collections import Counter

# **修复**：设置Windows控制台编码为UTF-8
try:
    from src.utils.encoding_fix import fix_windows_console_encoding
    fix_windows_console_encoding()
except ImportError:
    # 如果导入失败，使用备用方案
    if sys.platform == 'win32':
        try:
            import io
            # 只在必要时设置编码，避免文件操作冲突
            if hasattr(sys.stdout, 'buffer') and not isinstance(sys.stdout, io.TextIOWrapper):
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            if hasattr(sys.stderr, 'buffer') and not isinstance(sys.stderr, io.TextIOWrapper):
                sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        except (AttributeError, ValueError, OSError):
            # 如果设置失败，继续执行
            pass

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.rl_agent.model import GuandanPolicyNet
from src.knowledge_processor.replay_parser import ReplayParser
from src.train.pretrain import GuandanDataset
from torch.utils.data import DataLoader

# 导入状态编码函数（从pretrain.py中提取）
def card_to_index(card_code):
    """与 rl_decision_engine.py 中的编码方式完全一致"""
    suit_map = {'S': 0, 'H': 1, 'C': 2, 'D': 3}
    rank_map = {
        '2': 0, '3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6, '9': 7,
        'T': 8, 'J': 9, 'Q': 10, 'K': 11, 'A': 12,
        'B': 13,  # 小王
        'R': 14   # 大王
    }
    if len(card_code) >= 2:
        suit = card_code[0]
        rank = card_code[1]
        suit_val = suit_map.get(suit, 0)
        rank_val = rank_map.get(rank, 0)
        idx = suit_val * 15 + rank_val
        return min(idx, 59)  # 确保在0-59范围内
    return 0

def index_to_card(card_idx):
    """将索引转换回卡牌代码"""
    suit_map = {0: 'S', 1: 'H', 2: 'C', 3: 'D'}
    rank_map = {
        0: '2', 1: '3', 2: '4', 3: '5', 4: '6', 5: '7', 6: '8', 7: '9',
        8: 'T', 9: 'J', 10: 'Q', 11: 'K', 12: 'A',
        13: 'B', 14: 'R'
    }
    if card_idx < 60:
        suit_idx = card_idx // 15
        rank_idx = card_idx % 15
        suit = suit_map.get(suit_idx, 'S')
        rank = rank_map.get(rank_idx, '2')
        return f"{suit}{rank}"
    return None


def identify_strategy_type(state_dict, action_cards, last_action=None):
    """
    识别动作的策略类型（增强版：包含7种策略类型）
    
    Args:
        state_dict: 状态字典
        action_cards: 动作卡牌列表
        last_action: 上一步动作
    
    Returns:
        strategy_type: 
        - 'bomb'（出炸弹）
        - 'suppress'（压制对手）
        - 'protect'（保护队友）
        - 'control'（控牌）
        - 'group'（组牌）
        - 'follow'（跟牌）
        - 'discard'（顺牌/出牌）
        - 'unknown'（未知）
    """
    if not action_cards:
        return 'unknown'
    
    # 获取当前玩家手牌
    hand_cards = state_dict.get('hand', [])
    if not hand_cards:
        return 'unknown'
    
    action_type = state_dict.get('action_type', '')
    player_rest_cards = state_dict.get('player_rest_cards', [27, 27, 27, 27])
    current_player = state_dict.get('current_player', 0)
    
    # 计算队友和对手
    # 掼蛋是4人游戏，队友是(current_player + 2) % 4
    teammate = (current_player + 2) % 4
    opponents = [i for i in range(4) if i != current_player and i != teammate]
    
    # 获取对手和队友的剩余牌数
    opponent_rest_cards = [player_rest_cards[i] for i in opponents if i < len(player_rest_cards)]
    teammate_rest_cards = player_rest_cards[teammate] if teammate < len(player_rest_cards) else 27
    min_opponent_cards = min(opponent_rest_cards) if opponent_rest_cards else 27
    max_opponent_cards = max(opponent_rest_cards) if opponent_rest_cards else 27
    
    # 1. 判断是否是出炸弹（优先级最高，最明确）
    if action_type in ['Bomb', 'BOMB']:
        return 'bomb'
    
    # 2. 判断是否是保护队友
    # 保护队友的情况：
    # - 队友快走完（剩余牌数<=10），阻止对手传牌给队友的对手
    # - 对手为队友传牌时，及时阻截
    # - 对手传牌时，及时阻截（即使队友牌数较多，但队友牌数明显少于对手时）
    # - 队友牌数明显少于对手时，阻截对手的动作可能是保护队友
    if last_action:
        last_action_player = None
        # 从history中获取上一步动作的玩家
        history = state_dict.get('history', [])
        if history:
            last_history = history[-1]
            last_action_player = last_history.get('player')
        
        # 如果上一步是对手出的牌，当前动作能压制，可能是保护队友或压制对手
        if last_action_player is not None:
            if last_action_player in opponents:
                # 对手出的牌，当前动作能压制
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
    # 压制对手的情况：
    # - 对手快走完（剩余牌数<=8），使用大牌或炸弹压制
    # - 对手传牌时，及时阻截（已在上面处理）
    if min_opponent_cards <= 8:
        # 对手快走完，使用大牌压制
        # 如果出牌数量多（>=4），可能是压制
        if len(action_cards) >= 4 and action_type not in ['Bomb', 'BOMB']:
            return 'suppress'
        # 如果是对子、三带二等组合牌型，且对手快走完，可能是压制
        if action_type in ['Pair', 'Trips', 'ThreeWithTwo', 'Straight']:
            return 'suppress'
    
    # 4. 判断是否是控牌（对手快走完，使用炸弹或其他大牌）
    # 注意：控牌和压制对手的区别：
    # - 控牌：更注重控制节奏，防止对手冲刺
    # - 压制对手：更注重主动压制，阻止对手行动
    if min_opponent_cards <= 8:
        # 如果出牌数量多，且不是组合牌型，可能是控牌
        if len(action_cards) >= 4 and action_type not in ['Pair', 'Trips', 'ThreeWithTwo', 'Straight']:
            return 'control'
    
    # 5. 判断是否是跟牌（能压制上一步动作）
    if last_action and last_action.get('type') not in ['PASS', None, '']:
        last_action_type = last_action.get('type', '')
        
        # 如果动作类型相同，可能是跟牌
        if action_type == last_action_type and action_type not in ['PASS', '']:
            # 简化判断：如果能压制，就是跟牌
            return 'follow'
    
    # 6. 判断是否是组牌（减少手数、减少单牌）
    # 简化：如果出的是组合牌型（对子、三带二等），可能是组牌
    if action_type in ['Pair', 'Trips', 'ThreeWithTwo', 'Straight', 'ThreePair', 'TwoTrips']:
        return 'group'
    
    # 7. 其他情况：顺牌/出牌
    return 'discard'


def evaluate_strategy_types():
    """评估策略类型匹配率"""
    print("="*60)
    print("策略类型分析评估")
    print("="*60)
    print(f"评估时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 1. 加载模型和数据
    model_path = "models/bc_model_v1.pth"
    if not os.path.exists(model_path):
        print(f"[ERROR] 模型文件不存在: {model_path}")
        return
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # 加载模型时，需要检查是否有策略分类头和模型保存格式
    try:
        checkpoint = torch.load(model_path, map_location=device, weights_only=False)
        
        # 处理不同的模型保存格式
        if isinstance(checkpoint, dict):
            # 新格式：包含 model_state_dict 键的字典
            if 'model_state_dict' in checkpoint:
                model_state_dict = checkpoint['model_state_dict']
            # 旧格式：直接是 state_dict
            elif any(key.startswith('fc') or key.startswith('strategy') for key in checkpoint.keys()):
                model_state_dict = checkpoint
            else:
                # 如果字典中没有模型相关的键，尝试使用整个字典
                print("[WARNING] 无法识别模型格式，尝试直接加载...")
                model_state_dict = checkpoint
        else:
            # 直接是 state_dict
            model_state_dict = checkpoint
        
        # 检查是否有策略分类头
        has_strategy_head = 'fc_strategy.weight' in model_state_dict
        
        model = GuandanPolicyNet(
            input_dim=512, 
            hidden_dim=256, 
            output_dim=512,
            enable_strategy_head=has_strategy_head
        ).to(device)
        
        # 加载模型状态，允许部分匹配（strict=False）以兼容不同格式
        try:
            model.load_state_dict(model_state_dict, strict=True)
        except RuntimeError as e:
            # 如果严格加载失败，尝试非严格加载
            print(f"[WARNING] 严格加载失败，尝试非严格加载: {e}")
            model.load_state_dict(model_state_dict, strict=False)
        
        print(f"[OK] 模型加载成功")
    except Exception as e:
        print(f"[ERROR] 模型加载失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    model.eval()
    
    # 加载训练数据
    try:
        parser = ReplayParser("game_records")
        replays = parser.load_replays()
        raw_data = parser.extract_training_data(replays)
        
        print(f"\n数据信息:")
        print(f"  对局文件数: {len(replays)} 个")
        print(f"  训练样本数: {len(raw_data)} 个")
        
        if len(raw_data) == 0:
            print("[ERROR] 没有训练数据")
            return
    except Exception as e:
        print(f"[ERROR] 加载训练数据失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 2. 评估策略类型匹配率
    dataset = GuandanDataset(raw_data)
    dataloader = DataLoader(dataset, batch_size=32, shuffle=False)
    
    strategy_stats = {
        'group': {'expert': 0, 'predicted': 0, 'match': 0},
        'follow': {'expert': 0, 'predicted': 0, 'match': 0},
        'control': {'expert': 0, 'predicted': 0, 'match': 0},
        'discard': {'expert': 0, 'predicted': 0, 'match': 0},
        'unknown': {'expert': 0, 'predicted': 0, 'match': 0}
    }
    
    total_samples = 0
    total_matches = 0
    
    print(f"\n开始评估...")
    try:
        with torch.no_grad():
            for batch_idx, batch_data in enumerate(dataloader):
                try:
                    # 处理不同的数据格式（可能是2个或4个值）
                    if len(batch_data) == 2:
                        state_vec, action_vec = batch_data
                    elif len(batch_data) == 4:
                        state_vec, action_vec, strategy_type_idx, pattern_type_idx = batch_data
                    else:
                        print(f"[ERROR] 意外的数据格式，包含 {len(batch_data)} 个值")
                        continue
                    
                    state_vec = state_vec.to(device)
                    action_vec = action_vec.to(device)
                    
                    # 获取模型预测
                    # **基线评估参数**：使用阶段0验证的标准参数作为统一标尺
                    predicted_action = model.get_action(state_vec, threshold=0.3, scaling_factor=5.0)
                    
                    # 对每个样本
                    batch_size = state_vec.size(0)
                    for i in range(batch_size):
                        try:
                            total_samples += 1
                            
                            # 获取状态和动作
                            state = state_vec[i].cpu().numpy()
                            expert_action = action_vec[i].cpu().numpy()
                            predicted = predicted_action[i]
                            
                            # 重建状态字典（简化版）
                            # 注意：这里需要从state_vec重建state_dict，实际实现可能需要更复杂
                            # 为了简化，我们使用原始数据
                            sample_idx = batch_idx * dataloader.batch_size + i
                            if sample_idx < len(raw_data):
                                state_dict, expert_cards = raw_data[sample_idx]
                                
                                # 识别专家动作的策略类型
                                # 从history中提取last_action
                                history = state_dict.get('history', [])
                                last_action = None
                                if history:
                                    # history格式可能是 [{'player': 0, 'action': [...]}, ...]
                                    last_action = history[-1] if isinstance(history[-1], dict) else {}
                                
                                expert_strategy = identify_strategy_type(state_dict, expert_cards, last_action)
                                
                                # 识别预测动作的策略类型
                                # 将预测的action_vec转换为卡牌列表
                                predicted_cards = []
                                for j, val in enumerate(predicted):
                                    if val > 0.5:  # 阈值
                                        # 将索引转换为卡牌
                                        card = index_to_card(j)
                                        if card:
                                            predicted_cards.append(card)
                                
                                predicted_strategy = identify_strategy_type(state_dict, predicted_cards, last_action)
                                
                                # 统计
                                strategy_stats[expert_strategy]['expert'] += 1
                                strategy_stats[predicted_strategy]['predicted'] += 1
                                
                                if expert_strategy == predicted_strategy:
                                    strategy_stats[expert_strategy]['match'] += 1
                                    total_matches += 1
                            
                            if total_samples % 100 == 0:
                                print(f"  已处理 {total_samples} 个样本...")
                        except Exception as e:
                            print(f"  [WARNING] 处理样本 {total_samples} 时出错: {e}")
                            continue
                except Exception as e:
                    print(f"  [WARNING] 处理批次 {batch_idx} 时出错: {e}")
                    continue
    except Exception as e:
        print(f"[ERROR] 评估过程出错: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 3. 统计和报告
    print(f"\n" + "="*60)
    print("策略类型匹配率统计")
    print("="*60)
    
    print(f"\n总体匹配率: {total_matches}/{total_samples} = {total_matches/total_samples*100:.2f}%")
    
    print(f"\n各策略类型统计:")
    print(f"{'策略类型':<10} {'专家次数':<10} {'预测次数':<10} {'匹配次数':<10} {'匹配率':<10}")
    print("-"*60)
    
    for strategy_type, stats in strategy_stats.items():
        if stats['expert'] > 0:
            match_rate = stats['match'] / stats['expert'] * 100
            print(f"{strategy_type:<10} {stats['expert']:<10} {stats['predicted']:<10} {stats['match']:<10} {match_rate:<10.2f}%")
    
    # 4. 保存结果
    result = {
        'evaluation_time': datetime.now().isoformat(),
        'total_samples': total_samples,
        'total_matches': total_matches,
        'overall_match_rate': total_matches/total_samples*100 if total_samples > 0 else 0,
        'strategy_stats': {k: dict(v) for k, v in strategy_stats.items()}
    }
    
    result_file = f"training_logs/strategy_types_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs(os.path.dirname(result_file), exist_ok=True)
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n[OK] 评估结果已保存到: {result_file}")
    print("\n" + "="*60)
    print("评估完成")
    print("="*60)


if __name__ == "__main__":
    evaluate_strategy_types()

