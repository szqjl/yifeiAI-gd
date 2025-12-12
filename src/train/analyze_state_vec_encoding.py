# -*- coding: utf-8 -*-
"""
分析state_vec编码问题
重点分析：为什么83.8%的维度总是为0
"""

import sys
import os
import torch
import numpy as np
from collections import Counter, defaultdict
from datetime import datetime

# 修复Windows控制台编码
if sys.platform == 'win32':
    try:
        import io
        if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        if not isinstance(sys.stderr, io.TextIOWrapper) or sys.stderr.encoding != 'utf-8':
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.knowledge_processor.replay_parser import ReplayParser
from src.train.pretrain import GuandanDataset
from torch.utils.data import DataLoader


def analyze_state_vec_structure():
    """分析state_vec的结构和编码逻辑"""
    print("="*60)
    print("state_vec编码结构分析")
    print("="*60)
    
    # 根据pretrain.py中的编码逻辑，分析每个维度的用途
    dimension_info = [
        (0, 60, "手牌编码", "card_to_index编码，最多60个位置"),
        (60, 120, "未使用", "预留空间，当前未使用"),
        (120, 123, "游戏阶段", "0=开局, 1=中期, 2=残局"),
        (123, 127, "玩家剩余牌数", "4个玩家，归一化到[0,1]"),
        (127, 137, "动作类型", "10种动作类型（PASS, Single, Pair等）"),
        (137, 152, "动作牌点", "15种牌点（2,3,4...A,B,R）"),
        (152, 155, "策略标志", "can_follow, can_followup, need_control"),
        (155, 163, "策略类型", "8种策略类型（bomb, suppress等）"),
        (163, 164, "策略效果", "策略效果分数，归一化到[0,1]"),
        (164, 512, "历史动作", "348个维度，每个动作17维，最多20个历史动作"),
    ]
    
    print("\n维度分配情况：")
    total_used = 0
    for start, end, name, desc in dimension_info:
        size = end - start
        total_used += size
        print(f"  维度 {start:3d}-{end-1:3d}: {size:3d}维 - {name:12s} ({desc})")
    
    print(f"\n总计: {total_used}维（应该是512维）")
    
    # 分析哪些维度应该被填充但实际没有被填充
    print("\n" + "="*60)
    print("编码逻辑检查")
    print("="*60)
    
    print("\n1. 手牌编码（0-59维）：")
    print("   - 代码：state_vec[card_idx] = 1.0 (card_idx < 60)")
    print("   - 问题：如果手牌数量少，很多维度会是0（正常）")
    
    print("\n2. 游戏阶段（120-122维）：")
    print("   - 代码：state_vec[120 + game_phase] = 1.0")
    print("   - 问题：如果game_phase缺失，使用默认值121（中期）")
    
    print("\n3. 玩家剩余牌数（123-126维）：")
    print("   - 代码：state_vec[123 + i] = card_count / 27.0")
    print("   - 问题：如果player_rest_cards缺失，使用默认值[27,27,27,27]")
    
    print("\n4. 动作类型（127-136维）：")
    print("   - 代码：state_vec[127 + action_type_idx] = 1.0")
    print("   - 问题：如果last_action缺失，这部分会是0")
    
    print("\n5. 动作牌点（137-151维）：")
    print("   - 代码：state_vec[137 + rank_idx] = 1.0")
    print("   - 问题：如果last_action或last_action_cards缺失，这部分会是0")
    
    print("\n6. 策略标志（152-154维）：")
    print("   - 代码：state_vec[152] = state_dict.get('can_follow', 0.0)")
    print("   - 问题：如果state_dict中没有这些字段，会是0.0")
    
    print("\n7. 策略类型（155-162维）：")
    print("   - 代码：state_vec[155 + strategy_type_idx] = 1.0")
    print("   - 问题：如果strategy_type缺失，使用默认值'unknown'（索引7）")
    
    print("\n8. 策略效果（163维）：")
    print("   - 代码：state_vec[163] = min(strategy_effectiveness / 30.0, 1.0)")
    print("   - 问题：如果strategy_effectiveness缺失，会是0.0")
    
    print("\n9. 历史动作（164-511维）：")
    print("   - 代码：❌ 完全没有编码逻辑！")
    print("   - 问题：这348个维度总是为0，因为代码中没有实现历史动作编码")
    
    return dimension_info


def analyze_actual_data(dataset, max_samples=1000):
    """分析实际数据中的state_vec填充情况"""
    print("\n" + "="*60)
    print("实际数据填充情况分析")
    print("="*60)
    
    # 收集state_vec
    state_vecs = []
    state_dicts = []
    indices = np.random.choice(len(dataset), min(max_samples, len(dataset)), replace=False)
    
    print(f"\n采样 {len(indices)} 个样本进行分析...")
    for idx in indices:
        state_vec, _, _, _ = dataset[idx]
        state_vecs.append(state_vec.numpy())
        # 获取原始state_dict
        state_dict, _ = dataset.data[idx]
        state_dicts.append(state_dict)
    
    state_vecs = np.array(state_vecs)
    
    # 分析每个部分的填充情况
    parts = [
        (0, 60, "手牌编码"),
        (60, 120, "未使用"),
        (120, 123, "游戏阶段"),
        (123, 127, "玩家剩余牌数"),
        (127, 137, "动作类型"),
        (137, 152, "动作牌点"),
        (152, 155, "策略标志"),
        (155, 163, "策略类型"),
        (163, 164, "策略效果"),
        (164, 512, "历史动作"),
    ]
    
    print("\n各部分填充情况：")
    for start, end, name in parts:
        part_vecs = state_vecs[:, start:end]
        non_zero_count = np.sum(part_vecs != 0)
        total_size = part_vecs.size
        non_zero_ratio = non_zero_count / total_size if total_size > 0 else 0
        
        # 检查有多少样本在这个部分有非零值
        samples_with_data = np.sum(np.any(part_vecs != 0, axis=1))
        sample_ratio = samples_with_data / len(state_vecs) if len(state_vecs) > 0 else 0
        
        print(f"  {name:12s} (维度 {start:3d}-{end-1:3d}): "
              f"非零比例 {non_zero_ratio*100:5.1f}%, "
              f"有数据的样本 {sample_ratio*100:5.1f}%")
    
    # 分析state_dict中的数据可用性
    print("\n" + "="*60)
    print("state_dict数据可用性分析")
    print("="*60)
    
    field_stats = defaultdict(int)
    for state_dict in state_dicts:
        # 检查各个字段是否存在
        if 'hand' in state_dict and state_dict['hand']:
            field_stats['hand'] += 1
        if 'history' in state_dict and state_dict['history']:
            field_stats['history'] += 1
        if 'last_action' in state_dict and state_dict['last_action']:
            field_stats['last_action'] += 1
        if 'game_phase' in state_dict:
            field_stats['game_phase'] += 1
        if 'player_rest_cards' in state_dict:
            field_stats['player_rest_cards'] += 1
        if 'can_follow' in state_dict:
            field_stats['can_follow'] += 1
        if 'can_followup' in state_dict:
            field_stats['can_followup'] += 1
        if 'need_control' in state_dict:
            field_stats['need_control'] += 1
        if 'strategy_type' in state_dict:
            field_stats['strategy_type'] += 1
        if 'strategy_effectiveness' in state_dict:
            field_stats['strategy_effectiveness'] += 1
    
    print(f"\n字段存在情况（共{len(state_dicts)}个样本）：")
    for field, count in sorted(field_stats.items()):
        ratio = count / len(state_dicts) * 100
        print(f"  {field:20s}: {count:5d} ({ratio:5.1f}%)")
    
    # 分析history字段的详细情况
    print("\n" + "="*60)
    print("历史动作（history）字段详细分析")
    print("="*60)
    
    history_lengths = []
    history_samples = 0
    for state_dict in state_dicts:
        if 'history' in state_dict and state_dict['history']:
            history_samples += 1
            history_lengths.append(len(state_dict['history']))
    
    if history_lengths:
        print(f"\n有历史动作的样本数: {history_samples} ({history_samples/len(state_dicts)*100:.1f}%)")
        print(f"历史动作长度统计:")
        print(f"  平均长度: {np.mean(history_lengths):.1f}")
        print(f"  中位数: {np.median(history_lengths):.1f}")
        print(f"  最小值: {int(np.min(history_lengths))}")
        print(f"  最大值: {int(np.max(history_lengths))}")
        print(f"  长度分布:")
        length_counts = Counter(history_lengths)
        for length, count in sorted(length_counts.items())[:10]:
            print(f"    长度 {length:2d}: {count:4d} 次 ({count/len(history_lengths)*100:5.1f}%)")
    else:
        print("\n❌ 没有样本包含历史动作数据！")
    
    return state_vecs, state_dicts


def suggest_fixes():
    """提出修复建议"""
    print("\n" + "="*60)
    print("修复建议")
    print("="*60)
    
    print("\n1. 历史动作编码（164-511维，348个维度）：")
    print("   - 问题：代码中完全没有实现历史动作编码")
    print("   - 建议：实现历史动作编码逻辑")
    print("   - 方案：")
    print("     * 从state_dict['history']中提取最近N个动作（N<=20）")
    print("     * 每个动作编码为17维：")
    print("       - 动作类型（10维）")
    print("       - 动作牌点（15维）")
    print("       - 动作玩家（2维，可选）")
    print("     * 从维度164开始，每17维编码一个历史动作")
    print("     * 如果历史动作少于20个，剩余维度保持为0")
    
    print("\n2. 策略标志（152-154维）：")
    print("   - 问题：如果state_dict中没有这些字段，会是0.0")
    print("   - 建议：从游戏状态中计算这些标志，而不是依赖state_dict")
    
    print("\n3. 策略类型和效果（155-163维）：")
    print("   - 问题：如果state_dict中没有这些字段，会是默认值或0.0")
    print("   - 建议：从游戏状态中计算策略信息，而不是依赖state_dict")
    
    print("\n4. 维度60-119（未使用）：")
    print("   - 问题：这60个维度完全未使用")
    print("   - 建议：可以考虑用于编码其他信息，或者压缩state_vec大小")


def main():
    print("="*60)
    print("state_vec编码问题分析")
    print("="*60)
    print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. 分析state_vec结构
    dimension_info = analyze_state_vec_structure()
    
    # 2. 加载数据
    print("\n" + "="*60)
    print("加载数据...")
    print("="*60)
    parser = ReplayParser("game_records")
    replays = parser.load_replays()
    raw_data = parser.extract_training_data(replays)
    
    if len(raw_data) == 0:
        print("[ERROR] 没有找到训练数据")
        return
    
    print(f"[OK] 加载了 {len(raw_data)} 个样本")
    
    # 创建数据集
    dataset = GuandanDataset(raw_data)
    print(f"[OK] 数据集大小: {len(dataset)}")
    
    # 3. 分析实际数据
    state_vecs, state_dicts = analyze_actual_data(dataset, max_samples=1000)
    
    # 4. 提出修复建议
    suggest_fixes()
    
    print("\n" + "="*60)
    print("分析完成")
    print("="*60)


if __name__ == "__main__":
    main()

