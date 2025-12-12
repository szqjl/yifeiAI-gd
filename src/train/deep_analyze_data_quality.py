# -*- coding: utf-8 -*-
"""
深入分析数据质量问题
重点分析：
1. state_vec的维度分布（哪些维度总是为0，哪些维度有信息）
2. state_vec各维度的含义和填充情况
3. action_vec的索引分布（哪些索引最常被选中）
4. 数据不平衡问题（某些索引出现频率过高）
5. 状态信息完整性（缺失的关键信息）
6. 数据编码问题（是否存在编码错误）
"""

import sys
import os
import torch
import numpy as np
import json
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


def analyze_state_vec_dimensions(dataset, max_samples=5000):
    """深入分析state_vec的维度分布"""
    print("="*60)
    print("1. state_vec维度分布分析")
    print("="*60)
    
    # 收集所有state_vec
    state_vecs = []
    indices = np.random.choice(len(dataset), min(max_samples, len(dataset)), replace=False)
    
    print(f"采样 {len(indices)} 个样本进行分析...")
    for idx in indices:
        state_vec, _, _, _ = dataset[idx]
        state_vecs.append(state_vec.numpy())
    
    state_vecs = np.array(state_vecs)
    print(f"收集到 {len(state_vecs)} 个state_vec，维度: {state_vecs.shape}")
    
    # 分析每个维度的使用情况
    dim_info = []
    for dim in range(512):
        non_zero_count = np.sum(state_vecs[:, dim] != 0)
        non_zero_ratio = non_zero_count / len(state_vecs)
        mean_value = np.mean(state_vecs[:, dim])
        std_value = np.std(state_vecs[:, dim])
        max_value = np.max(state_vecs[:, dim])
        min_value = np.min(state_vecs[:, dim])
        
        dim_info.append({
            'dim': dim,
            'non_zero_count': non_zero_count,
            'non_zero_ratio': non_zero_ratio,
            'mean': mean_value,
            'std': std_value,
            'max': max_value,
            'min': min_value
        })
    
    # 按非零比例排序
    dim_info.sort(key=lambda x: x['non_zero_ratio'], reverse=True)
    
    # 统计维度使用情况
    always_zero = [d for d in dim_info if d['non_zero_ratio'] == 0]
    rarely_used = [d for d in dim_info if 0 < d['non_zero_ratio'] < 0.01]
    sometimes_used = [d for d in dim_info if 0.01 <= d['non_zero_ratio'] < 0.1]
    often_used = [d for d in dim_info if 0.1 <= d['non_zero_ratio'] < 0.5]
    frequently_used = [d for d in dim_info if d['non_zero_ratio'] >= 0.5]
    
    print(f"\n维度使用情况统计:")
    print(f"  总是为0: {len(always_zero)} 个维度 ({len(always_zero)/512*100:.1f}%)")
    print(f"  很少使用 (<1%): {len(rarely_used)} 个维度 ({len(rarely_used)/512*100:.1f}%)")
    print(f"  偶尔使用 (1-10%): {len(sometimes_used)} 个维度 ({len(sometimes_used)/512*100:.1f}%)")
    print(f"  经常使用 (10-50%): {len(often_used)} 个维度 ({len(often_used)/512*100:.1f}%)")
    print(f"  频繁使用 (≥50%): {len(frequently_used)} 个维度 ({len(frequently_used)/512*100:.1f}%)")
    
    # 显示总是为0的维度范围
    if always_zero:
        always_zero_dims = [d['dim'] for d in always_zero]
        print(f"\n总是为0的维度范围:")
        print(f"  维度索引: {min(always_zero_dims)} - {max(always_zero_dims)}")
        # 检查是否有连续的范围
        ranges = []
        start = always_zero_dims[0]
        for i in range(1, len(always_zero_dims)):
            if always_zero_dims[i] != always_zero_dims[i-1] + 1:
                ranges.append((start, always_zero_dims[i-1]))
                start = always_zero_dims[i]
        ranges.append((start, always_zero_dims[-1]))
        print(f"  连续范围: {ranges[:10]}...")  # 只显示前10个范围
    
    # 显示最常用的维度
    print(f"\n最常用的10个维度:")
    for i, d in enumerate(frequently_used[:10]):
        print(f"  维度 {d['dim']:3d}: 使用率 {d['non_zero_ratio']*100:5.1f}%, "
              f"均值 {d['mean']:.4f}, 标准差 {d['std']:.4f}")
    
    # 分析维度含义（根据pretrain.py中的编码规则）
    print(f"\n维度含义分析（根据编码规则）:")
    print(f"  维度 0-119: 手牌（108张卡牌 + 12个位置）")
    print(f"  维度 120-122: 游戏阶段（3个维度）")
    print(f"  维度 123-126: 玩家剩余牌数（4个维度）")
    print(f"  维度 127-136: 动作类型（10个维度）")
    print(f"  维度 137-151: 级牌（15个维度）")
    print(f"  维度 152-154: 策略标志（3个维度：can_follow, can_followup, need_control）")
    print(f"  维度 155-162: 策略类型（8个维度）")
    print(f"  维度 163: 策略效果（1个维度）")
    print(f"  维度 164-511: 历史动作（348个维度，每个动作17维）")
    
    # 检查各部分的填充情况
    print(f"\n各部分填充情况:")
    parts = [
        (0, 120, "手牌"),
        (120, 123, "游戏阶段"),
        (123, 127, "玩家剩余牌数"),
        (127, 137, "动作类型"),
        (137, 152, "级牌"),
        (152, 155, "策略标志"),
        (155, 163, "策略类型"),
        (163, 164, "策略效果"),
        (164, 512, "历史动作")
    ]
    
    for start, end, name in parts:
        part_vecs = state_vecs[:, start:end]
        non_zero_ratio = np.sum(part_vecs != 0) / part_vecs.size
        print(f"  {name} (维度 {start}-{end-1}): 非零比例 {non_zero_ratio*100:.1f}%")
    
    return dim_info, state_vecs


def analyze_action_vec_distribution(dataset, max_samples=5000):
    """深入分析action_vec的索引分布"""
    print("\n" + "="*60)
    print("2. action_vec索引分布分析")
    print("="*60)
    
    # 收集所有action_vec
    action_vecs = []
    card_counts = []
    indices = np.random.choice(len(dataset), min(max_samples, len(dataset)), replace=False)
    
    print(f"采样 {len(indices)} 个样本进行分析...")
    for idx in indices:
        _, action_vec, _, _ = dataset[idx]
        action_vec = action_vec.numpy()
        action_vecs.append(action_vec)
        card_counts.append(np.sum(action_vec))
    
    action_vecs = np.array(action_vecs)
    print(f"收集到 {len(action_vecs)} 个action_vec，维度: {action_vecs.shape}")
    
    # 统计每个索引被选中的次数
    index_counts = np.sum(action_vecs, axis=0)
    index_ratios = index_counts / len(action_vecs)
    
    # 找出最常被选中的索引
    top_indices = np.argsort(index_counts)[::-1][:20]
    
    print(f"\n最常被选中的20个索引:")
    for i, idx in enumerate(top_indices):
        count = int(index_counts[idx])
        ratio = index_ratios[idx]
        print(f"  索引 {idx:3d}: {count:5d} 次 ({ratio*100:5.1f}%)")
    
    # 分析索引分布的不平衡性
    non_zero_indices = np.sum(index_counts > 0)
    print(f"\n索引分布统计:")
    print(f"  有数据的索引数: {non_zero_indices} / 512 ({non_zero_indices/512*100:.1f}%)")
    print(f"  总是为0的索引数: {512 - non_zero_indices} ({(512-non_zero_indices)/512*100:.1f}%)")
    
    # 计算不平衡度（Gini系数）
    sorted_counts = np.sort(index_counts[index_counts > 0])
    n = len(sorted_counts)
    cumsum = np.cumsum(sorted_counts)
    gini = (2 * np.sum((np.arange(1, n+1)) * sorted_counts)) / (n * np.sum(sorted_counts)) - (n + 1) / n
    print(f"  不平衡度 (Gini系数): {gini:.4f} (0=完全平衡, 1=完全不平衡)")
    
    # 分析卡牌数分布
    card_counts = np.array(card_counts)
    print(f"\n卡牌数分布:")
    print(f"  平均卡牌数: {np.mean(card_counts):.2f} 张")
    print(f"  中位数: {np.median(card_counts):.2f} 张")
    print(f"  标准差: {np.std(card_counts):.2f} 张")
    print(f"  最小值: {int(np.min(card_counts))} 张")
    print(f"  最大值: {int(np.max(card_counts))} 张")
    
    # 卡牌数分布直方图
    unique_counts, counts = np.unique(card_counts, return_counts=True)
    print(f"\n卡牌数分布详情:")
    for count, freq in zip(unique_counts[:20], counts[:20]):
        print(f"  {int(count)} 张: {freq} 次 ({freq/len(card_counts)*100:.1f}%)")
    
    return index_counts, index_ratios, card_counts


def analyze_data_encoding_issues(dataset, max_samples=1000):
    """分析数据编码问题"""
    print("\n" + "="*60)
    print("3. 数据编码问题分析")
    print("="*60)
    
    # 检查是否有异常样本
    anomalies = []
    indices = np.random.choice(len(dataset), min(max_samples, len(dataset)), replace=False)
    
    print(f"检查 {len(indices)} 个样本的编码问题...")
    for idx in indices:
        state_vec, action_vec, _, _ = dataset[idx]
        state_vec = state_vec.numpy()
        action_vec = action_vec.numpy()
        
        # 检查1: action_vec是否有超过27张卡牌（不合理）
        card_count = np.sum(action_vec)
        if card_count > 27:
            anomalies.append({
                'idx': idx,
                'type': 'too_many_cards',
                'card_count': card_count
            })
        
        # 检查2: state_vec是否全为0（无状态信息）
        if np.sum(state_vec) == 0:
            anomalies.append({
                'idx': idx,
                'type': 'empty_state',
                'card_count': card_count
            })
        
        # 检查3: action_vec是否全为0（可能是PASS，但需要验证）
        if card_count == 0:
            # 检查state_vec中是否有相关信息表明这是PASS
            # 这里可以添加更多检查逻辑
            pass
    
    print(f"\n发现 {len(anomalies)} 个异常样本:")
    anomaly_types = Counter([a['type'] for a in anomalies])
    for anomaly_type, count in anomaly_types.items():
        print(f"  {anomaly_type}: {count} 个")
    
    return anomalies


def analyze_state_action_correlation(dataset, max_samples=2000):
    """分析状态和动作的相关性"""
    print("\n" + "="*60)
    print("4. 状态-动作相关性分析")
    print("="*60)
    
    # 收集状态和动作
    state_vecs = []
    action_vecs = []
    indices = np.random.choice(len(dataset), min(max_samples, len(dataset)), replace=False)
    
    print(f"分析 {len(indices)} 个样本的状态-动作相关性...")
    for idx in indices:
        state_vec, action_vec, _, _ = dataset[idx]
        state_vecs.append(state_vec.numpy())
        action_vecs.append(action_vec.numpy())
    
    state_vecs = np.array(state_vecs)
    action_vecs = np.array(action_vecs)
    
    # 计算状态维度和动作索引的相关性
    # 对于每个动作索引，找出哪些状态维度与其最相关
    print(f"\n分析状态维度对动作预测的影响...")
    
    # 对于最常被选中的动作索引，分析哪些状态维度与其相关
    action_index_counts = np.sum(action_vecs, axis=0)
    top_action_indices = np.argsort(action_index_counts)[::-1][:10]
    
    print(f"\n最常被选中的10个动作索引及其相关的状态维度:")
    for action_idx in top_action_indices:
        # 找出选择该动作的样本
        selected_samples = action_vecs[:, action_idx] == 1
        if np.sum(selected_samples) == 0:
            continue
        
        # 计算这些样本中状态维度的平均值
        selected_states = state_vecs[selected_samples]
        avg_state = np.mean(selected_states, axis=0)
        
        # 找出最相关的状态维度（非零且值较大）
        relevant_dims = np.where(avg_state > 0.1)[0]
        
        print(f"\n  动作索引 {action_idx}:")
        print(f"    被选中次数: {int(action_index_counts[action_idx])}")
        print(f"    相关状态维度数: {len(relevant_dims)}")
        if len(relevant_dims) > 0:
            print(f"    主要相关维度: {relevant_dims[:10].tolist()}")
    
    return state_vecs, action_vecs


def main():
    print("="*60)
    print("深入数据质量分析")
    print("="*60)
    print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 加载数据
    print("加载数据...")
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
    
    # 1. 分析state_vec维度分布
    dim_info, state_vecs = analyze_state_vec_dimensions(dataset, max_samples=5000)
    
    # 2. 分析action_vec索引分布
    index_counts, index_ratios, card_counts = analyze_action_vec_distribution(dataset, max_samples=5000)
    
    # 3. 分析数据编码问题
    anomalies = analyze_data_encoding_issues(dataset, max_samples=1000)
    
    # 4. 分析状态-动作相关性
    state_vecs_corr, action_vecs_corr = analyze_state_action_correlation(dataset, max_samples=2000)
    
    # 保存分析结果
    result_file = f"training_logs/deep_data_quality_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    results = {
        'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_samples': int(len(dataset)),
        'state_vec_dimensions': {
            'always_zero_count': int(len([d for d in dim_info if d['non_zero_ratio'] == 0])),
            'dim_info_summary': [
                {
                    'dim': int(d['dim']),
                    'non_zero_count': int(d['non_zero_count']),
                    'non_zero_ratio': float(d['non_zero_ratio']),
                    'mean': float(d['mean']),
                    'std': float(d['std']),
                    'max': float(d['max']),
                    'min': float(d['min'])
                }
                for d in dim_info[:50]
            ]
        },
        'action_vec_distribution': {
            'top_indices': [int(idx) for idx in np.argsort(index_counts)[::-1][:20]],
            'top_index_counts': [int(count) for count in np.sort(index_counts)[::-1][:20]],
            'non_zero_indices_count': int(np.sum(index_counts > 0)),
            'card_count_stats': {
                'mean': float(np.mean(card_counts)),
                'median': float(np.median(card_counts)),
                'std': float(np.std(card_counts)),
                'min': int(np.min(card_counts)),
                'max': int(np.max(card_counts))
            }
        },
        'anomalies': [
            {
                'idx': int(a['idx']),
                'type': str(a['type']),
                'card_count': int(a['card_count'])
            }
            for a in anomalies[:100]
        ]
    }
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n分析结果已保存到: {result_file}")
    
    # 总结
    print("\n" + "="*60)
    print("分析总结")
    print("="*60)
    
    always_zero_dims = len([d for d in dim_info if d['non_zero_ratio'] == 0])
    print(f"1. state_vec维度问题:")
    print(f"   - {always_zero_dims} 个维度 ({always_zero_dims/512*100:.1f}%) 总是为0，信息不足")
    
    non_zero_indices = int(np.sum(index_counts > 0))
    print(f"\n2. action_vec分布问题:")
    print(f"   - 只有 {non_zero_indices} 个索引 ({non_zero_indices/512*100:.1f}%) 有数据")
    print(f"   - 索引分布不平衡，某些索引出现频率过高")
    
    print(f"\n3. 数据编码问题:")
    print(f"   - 发现 {len(anomalies)} 个异常样本")
    
    print(f"\n4. 建议:")
    print(f"   - 检查state_vec编码逻辑，确保关键信息被正确编码")
    print(f"   - 检查action_vec编码逻辑，确保卡牌索引正确")
    print(f"   - 考虑增加状态信息的完整性")
    print(f"   - 考虑数据平衡处理（如对稀有索引进行过采样）")


if __name__ == "__main__":
    main()

