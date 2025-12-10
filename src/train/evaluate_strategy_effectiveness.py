# -*- coding: utf-8 -*-
"""
策略效果评估脚本
评估模型选择的动作是否具有策略效果
"""

import sys
import os
import torch
import numpy as np
import json
from datetime import datetime

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
from src.knowledge_processor.strategy_encoder import StrategyEncoder
from src.train.pretrain import GuandanDataset
from torch.utils.data import DataLoader


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


def evaluate_strategy_effectiveness():
    """评估策略效果"""
    print("="*60)
    print("策略效果评估")
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
        checkpoint = torch.load(model_path, map_location=device)
        
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
    
    # 初始化策略编码器
    strategy_encoder = StrategyEncoder()
    
    # 加载replay数据（直接从replay中提取完整信息）
    try:
        parser = ReplayParser("game_records")
        replays = parser.load_replays()
        
        print(f"\n数据信息:")
        print(f"  对局文件数: {len(replays)} 个")
        
        if len(replays) == 0:
            print("[ERROR] 没有replay数据")
            return
    except Exception as e:
        print(f"[ERROR] 加载replay数据失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 2. 从replay数据中提取完整信息并评估策略效果
    effectiveness_stats = {
        'expert_scores': [],
        'predicted_scores': [],
        'score_differences': [],
        'expert_better': 0,
        'predicted_better': 0,
        'equal': 0
    }
    
    total_samples = 0
    valid_samples = 0
    skipped_empty_prediction = 0
    skipped_exception = 0
    
    # 卡牌编码函数（与pretrain.py保持一致）
    def card_to_index(card_code):
        suit_map = {'S': 0, 'H': 1, 'C': 2, 'D': 3}
        rank_map = {
            '2': 0, '3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6, '9': 7,
            'T': 8, 'J': 9, 'Q': 10, 'K': 11, 'A': 12,
            'B': 13, 'R': 14
        }
        if len(card_code) >= 2:
            suit = card_code[0]
            rank = card_code[1]
            suit_val = suit_map.get(suit, 0)
            rank_val = rank_map.get(rank, 0)
            idx = suit_val * 15 + rank_val
            return min(idx, 59)
        return 0
    
    def state_dict_to_vec(state_dict):
        """将state_dict转换为state_vec（与pretrain.py保持一致）"""
        state_vec = np.zeros(512, dtype=np.float32)
        
        # 1. Encode Hand (0-59维)
        for card in state_dict.get('hand', []):
            card_idx = card_to_index(card)
            if card_idx < 60:
                state_vec[card_idx] = 1.0
        
        # 2. 编码游戏阶段（120-122维）
        game_phase = state_dict.get('game_phase', 1)
        if game_phase < 3:
            state_vec[120 + game_phase] = 1.0
        else:
            state_vec[121] = 1.0
        
        # 3. 编码玩家剩余牌数（123-126维）
        player_rest_cards = state_dict.get('player_rest_cards', [27, 27, 27, 27])
        for i, card_count in enumerate(player_rest_cards[:4]):
            state_vec[123 + i] = card_count / 27.0
        
        # 4. 编码上一步动作（127-151维）
        last_action = state_dict.get('last_action', {})
        if last_action:
            action_type = last_action.get('type', '')
            action_cards = last_action.get('cards', [])
            
            action_type_map = {
                'PASS': 0, 'Single': 1, 'Pair': 2, 'Trips': 3,
                'Straight': 4, 'ThreeWithTwo': 5, 'Bomb': 6,
                'StraightFlush': 7, 'ThreePair': 8, 'TwoTrips': 9
            }
            action_type_idx = action_type_map.get(action_type, 0)
            if action_type_idx < 10:
                state_vec[127 + action_type_idx] = 1.0
            
            if action_cards:
                first_card = action_cards[0]
                rank_map = {
                    '2': 0, '3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6, '9': 7,
                    'T': 8, 'J': 9, 'Q': 10, 'K': 11, 'A': 12,
                    'B': 13, 'R': 14
                }
                if len(first_card) >= 2:
                    rank = first_card[1] if len(first_card) == 2 else first_card[1:2]
                    rank_idx = rank_map.get(rank, 0)
                    if rank_idx < 15:
                        state_vec[137 + rank_idx] = 1.0
        
        # 5. 编码策略特征（152-154维）
        state_vec[152] = state_dict.get('can_follow', 0.0)
        state_vec[153] = state_dict.get('can_followup', 0.0)
        state_vec[154] = state_dict.get('need_control', 0.0)
        
        return state_vec
    
    print(f"\n开始评估...")
    try:
        with torch.no_grad():
            for replay_idx, replay in enumerate(replays):
                try:
                    hero_id = replay.get('player_id')
                    hero_hand = set(replay.get('initial_hand', []))
                    all_hands_raw = replay.get('all_players_hands', {})
                    
                    # 转换all_hands为字典格式（键为玩家位置）
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
                    
                    history = []
                    
                    for action_idx, action_log in enumerate(replay.get('actions', [])):
                        try:
                            actor_pos = action_log['cur_pos']
                            action_str = action_log['cur_action']
                            action_type, cards_played = parser.parse_action_string(action_str)
                            
                            # 如果是Hero的回合，进行评估
                            if actor_pos == hero_id:
                                total_samples += 1
                                
                                # 构建完整的状态字典
                                # 计算玩家剩余牌数
                                player_rest_cards = []
                                for pos in range(4):
                                    if pos in all_hands and isinstance(all_hands[pos], list):
                                        player_rest_cards.append(len(all_hands[pos]))
                                    else:
                                        # 估算剩余牌数（简化：从初始手牌减去已出的牌）
                                        player_rest_cards.append(27)
                                
                                # 确定游戏阶段
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
                                    last_action = {
                                        'type': parser.parse_action_string(last_history.get('action_str', ''))[0],
                                        'cards': parser.parse_action_string(last_history.get('action_str', ''))[1]
                                    }
                                
                                # 构建完整状态字典
                                state_dict = {
                                    'hand': list(hero_hand),
                                    'history': history[-10:],
                                    'current_player': hero_id,
                                    'hands': all_hands,
                                    'last_action': last_action,
                                    'action_type': action_type,
                                    'game_phase': game_phase,
                                    'cur_rank': cur_rank,
                                    'player_rest_cards': player_rest_cards
                                }
                                
                                # 转换为状态向量
                                state_vec = state_dict_to_vec(state_dict)
                                state_tensor = torch.FloatTensor(state_vec).unsqueeze(0).to(device)
                                
                                # 获取模型原始输出（不经过get_action的阈值处理）
                                with torch.no_grad():
                                    logits = model.forward(state_tensor)
                                    probs = torch.sigmoid(logits)
                                    # **基线评估参数**：使用阶段0验证的标准参数作为统一标尺
                                    probs = probs * 5.0  # 基线缩放因子（阶段0基线参数）
                                    probs = torch.clamp(probs, 0, 1)
                                
                                # 将预测转换为卡牌列表（使用很低的阈值，确保能获取到预测）
                                predicted_cards = []
                                for j, val in enumerate(probs.squeeze(0)):
                                    if val > 0.05:  # 使用很低的阈值
                                        card = index_to_card(j)
                                        if card:
                                            predicted_cards.append(card)
                                
                                # 评估专家动作的策略效果（即使预测为空也评估专家动作）
                                try:
                                    # 确保hands字典格式正确（StrategyEncoder需要）
                                    hands_dict = {}
                                    for pos in range(4):
                                        if pos in all_hands:
                                            hands_dict[pos] = all_hands[pos] if isinstance(all_hands[pos], list) else list(all_hands[pos])
                                        else:
                                            hands_dict[pos] = []
                                    
                                    # 更新state_dict中的hands
                                    state_dict['hands'] = hands_dict
                                    expert_score = strategy_encoder.calculate_shaping_reward(
                                        state_dict=state_dict,
                                        action_cards=cards_played,
                                        action_type=action_type,
                                        game_phase=['opening', 'mid', 'endgame'][game_phase],
                                        cur_rank=cur_rank
                                    )
                                    
                                    effectiveness_stats['expert_scores'].append(expert_score)
                                    
                                    # 如果预测不为空，评估预测动作
                                    if predicted_cards:
                                        # 推断预测动作的类型（简化：根据卡牌数量推断）
                                        predicted_action_type = 'Single'
                                        if len(predicted_cards) == 2:
                                            predicted_action_type = 'Pair'
                                        elif len(predicted_cards) >= 3:
                                            predicted_action_type = 'Trips'
                                        
                                        # 评估预测动作的策略效果
                                        predicted_score = strategy_encoder.calculate_shaping_reward(
                                            state_dict=state_dict,
                                            action_cards=predicted_cards,
                                            action_type=predicted_action_type,
                                            game_phase=['opening', 'mid', 'endgame'][game_phase],
                                            cur_rank=cur_rank
                                        )
                                        
                                        effectiveness_stats['predicted_scores'].append(predicted_score)
                                        
                                        score_diff = expert_score - predicted_score
                                        effectiveness_stats['score_differences'].append(score_diff)
                                        
                                        if score_diff > 0.1:  # 专家更好
                                            effectiveness_stats['expert_better'] += 1
                                        elif score_diff < -0.1:  # 预测更好
                                            effectiveness_stats['predicted_better'] += 1
                                        else:  # 相等
                                            effectiveness_stats['equal'] += 1
                                    else:
                                        # 预测为空，只记录专家分数
                                        skipped_empty_prediction += 1
                                    
                                    valid_samples += 1
                                except Exception as e:
                                    # 跳过无法评估的样本
                                    skipped_exception += 1
                                    if skipped_exception <= 5:  # 只打印前5个错误
                                        print(f"    [DEBUG] 评估样本时出错: {e}")
                                    continue
                                
                                # 更新Hero的手牌
                                for card in cards_played:
                                    if card in hero_hand:
                                        hero_hand.remove(card)
                                
                                # 更新所有玩家的手牌
                                if hero_id in all_hands:
                                    all_hands[hero_id] = list(hero_hand)
                                
                                # 更新其他玩家的手牌（如果知道他们出了什么牌）
                                # 这里简化处理，只更新Hero的手牌
                            
                            # 更新历史
                            history.append({
                                'player': actor_pos,
                                'action_str': action_str,
                                'action': cards_played
                            })
                            
                        except Exception as e:
                            continue
                    
                    if (replay_idx + 1) % 100 == 0:
                        print(f"  已处理 {replay_idx + 1}/{len(replays)} 个对局，有效样本 {valid_samples} 个，跳过空预测 {skipped_empty_prediction} 个，跳过异常 {skipped_exception} 个...")
                        
                except Exception as e:
                    print(f"  [WARNING] 处理对局 {replay_idx} 时出错: {e}")
                    continue
                    
    except Exception as e:
        print(f"[ERROR] 评估过程出错: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 3. 统计和报告
    print(f"\n" + "="*60)
    print("策略效果评估统计")
    print("="*60)
    
    if valid_samples == 0:
        print("[ERROR] 没有有效的评估样本")
        return
    
    expert_avg = np.mean(effectiveness_stats['expert_scores']) if effectiveness_stats['expert_scores'] else 0.0
    
    print(f"\n总体统计:")
    print(f"  有效样本数（专家动作）: {valid_samples}")
    print(f"  专家平均策略效果: {expert_avg:.4f}")
    print(f"  跳过空预测样本数: {skipped_empty_prediction}")
    
    if effectiveness_stats['predicted_scores']:
        predicted_avg = np.mean(effectiveness_stats['predicted_scores'])
        avg_diff = np.mean(effectiveness_stats['score_differences'])
        
        print(f"  预测平均策略效果: {predicted_avg:.4f}")
        print(f"  平均效果差异: {avg_diff:.4f}")
        
        print(f"\n效果对比（有预测的样本）:")
        comparison_count = effectiveness_stats['expert_better'] + effectiveness_stats['predicted_better'] + effectiveness_stats['equal']
        if comparison_count > 0:
            print(f"  专家更好: {effectiveness_stats['expert_better']} ({effectiveness_stats['expert_better']/comparison_count*100:.2f}%)")
            print(f"  预测更好: {effectiveness_stats['predicted_better']} ({effectiveness_stats['predicted_better']/comparison_count*100:.2f}%)")
            print(f"  效果相等: {effectiveness_stats['equal']} ({effectiveness_stats['equal']/comparison_count*100:.2f}%)")
            
            # 计算效果匹配率（效果差异在合理范围内）
            reasonable_diff = [abs(d) <= 2.0 for d in effectiveness_stats['score_differences']]
            match_rate = sum(reasonable_diff) / len(reasonable_diff) * 100 if reasonable_diff else 0
            print(f"\n效果匹配率（差异≤2.0）: {sum(reasonable_diff)}/{len(reasonable_diff)} = {match_rate:.2f}%")
    else:
        print(f"\n⚠️ 警告: 所有样本的模型预测都为空，无法完成预测动作的策略效果评估")
        print(f"  可能原因:")
        print(f"    1. 模型输出概率过低（即使经过缩放后也低于阈值0.05）")
        print(f"    2. 状态向量编码可能存在问题")
        print(f"    3. 模型可能需要重新训练或调整参数")
        print(f"\n  已完成专家动作的策略效果评估，平均分数: {expert_avg:.4f}")
    
    # 4. 保存结果
    result = {
        'evaluation_time': datetime.now().isoformat(),
        'total_samples': total_samples,
        'valid_samples': valid_samples,
        'skipped_empty_prediction': skipped_empty_prediction,
        'expert_avg_score': float(expert_avg),
        'predicted_avg_score': float(np.mean(effectiveness_stats['predicted_scores'])) if effectiveness_stats['predicted_scores'] else None,
        'avg_score_difference': float(np.mean(effectiveness_stats['score_differences'])) if effectiveness_stats['score_differences'] else None,
        'expert_better_count': effectiveness_stats['expert_better'],
        'predicted_better_count': effectiveness_stats['predicted_better'],
        'equal_count': effectiveness_stats['equal'],
        'match_rate': float(np.mean([abs(d) <= 2.0 for d in effectiveness_stats['score_differences']])) * 100 if effectiveness_stats['score_differences'] else None,
        'note': '如果predicted_avg_score为None，说明所有样本的模型预测都为空'
    }
    
    result_file = f"training_logs/strategy_effectiveness_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs(os.path.dirname(result_file), exist_ok=True)
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n[OK] 评估结果已保存到: {result_file}")
    print("\n" + "="*60)
    print("评估完成")
    print("="*60)


if __name__ == "__main__":
    evaluate_strategy_effectiveness()

