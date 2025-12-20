# -*- coding: utf-8 -*-
"""
分析方案B训练后的数据质量，找出匹配率低的原因
重点分析：
1. 训练数据中action_vec的分布（每个样本有多少张卡牌）
2. 模型输出的概率分布
3. 预测卡牌数与真实卡牌数的对比
4. 是否存在数据质量问题（如action_vec编码错误、数据不平衡等）
5. 模型是否总是预测相同的卡牌索引
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

from src.rl_agent.model import GuandanPolicyNet
from src.knowledge_processor.replay_parser import ReplayParser
from src.train.pretrain import GuandanDataset
from torch.utils.data import DataLoader

def analyze_action_vec_distribution(dataset, max_samples=1000):
    """分析训练数据中action_vec的分布"""
    print("="*60)
    print("1. 训练数据中action_vec的分布分析")
    print("="*60)
    
    card_counts = []
    action_vec_samples = []
    sample_indices = []
    
    # 随机采样
    indices = np.random.choice(len(dataset), min(max_samples, len(dataset)), replace=False)
    
    for idx in indices:
        state_vec, action_vec, _, _ = dataset[idx]
        card_count = action_vec.sum().item()
        card_counts.append(card_count)
        action_vec_samples.append(action_vec.numpy())
        sample_indices.append(idx)
    
    card_counts = np.array(card_counts)
    
    print(f"\n分析样本数: {len(card_counts)}")
    print(f"\n真实卡牌数统计:")
    print(f"  最小值: {card_counts.min()}")
    print(f"  最大值: {card_counts.max()}")
    print(f"  平均值: {np.mean(card_counts):.2f}")
    print(f"  中位数: {np.median(card_counts):.2f}")
    print(f"  标准差: {np.std(card_counts):.2f}")
    
    # 卡牌数分布
    print(f"\n卡牌数分布:")
    card_count_dist = Counter(card_counts.astype(int))
    for count in sorted(card_count_dist.keys()):
        print(f"  {count}张: {card_count_dist[count]}个样本 ({card_count_dist[count]/len(card_counts)*100:.1f}%)")
    
    # 分析action_vec中哪些位置经常为1
    print(f"\n最常被选中的卡牌索引（Top 20）:")
    card_index_counts = defaultdict(int)
    for action_vec in action_vec_samples:
        indices = np.where(action_vec > 0.5)[0]
        for idx in indices:
            card_index_counts[int(idx)] += 1
    
    top_indices = sorted(card_index_counts.items(), key=lambda x: x[1], reverse=True)[:20]
    for idx, count in top_indices:
        print(f"  索引{idx}: {count}次 ({count/len(action_vec_samples)*100:.1f}%)")
    
    return card_counts, action_vec_samples, sample_indices

def analyze_model_output_distribution(model, dataset, device, sample_indices, max_samples=1000):
    """分析模型输出的概率分布"""
    print("\n" + "="*60)
    print("2. 模型输出概率分布分析")
    print("="*60)
    
    model.eval()
    all_probs = []
    all_scaled_probs = []
    all_logits = []
    true_card_counts = []
    predicted_card_counts = []
    
    # 只分析之前采样的样本
    limited_indices = sample_indices[:max_samples]
    
    with torch.no_grad():
        for idx in limited_indices:
            state_vec, action_vec, _, _ = dataset[idx]
            state_vec = state_vec.unsqueeze(0).to(device)
            action_vec = action_vec.to(device)
            
            logits = model(state_vec, return_strategy=False)
            probs = torch.sigmoid(logits)
            scaled_probs = probs * 5.0
            scaled_probs = torch.clamp(scaled_probs, 0, 1)
            
            all_logits.append(logits.cpu().numpy().flatten())
            all_probs.append(probs.cpu().numpy().flatten())
            all_scaled_probs.append(scaled_probs.cpu().numpy().flatten())
            
            true_count = action_vec.sum().item()
            true_card_counts.append(true_count)
            
            # 计算不同阈值下的预测卡牌数
            pred_count_03 = (scaled_probs > 0.3).sum().item()
            predicted_card_counts.append(pred_count_03)
    
    all_probs = np.array(all_probs)
    all_scaled_probs = np.array(all_scaled_probs)
    all_logits = np.array(all_logits)
    
    print(f"\n分析样本数: {len(all_probs)}")
    print(f"\n原始概率分布:")
    print(f"  最小值: {all_probs.min():.6f}")
    print(f"  最大值: {all_probs.max():.6f}")
    print(f"  平均值: {all_probs.mean():.6f}")
    print(f"  中位数: {np.median(all_probs):.6f}")
    print(f"  标准差: {all_probs.std():.6f}")
    
    # 统计概率为0的比例
    zero_prob_ratio = (all_probs == 0).sum() / all_probs.size
    print(f"  概率为0的比例: {zero_prob_ratio*100:.2f}%")
    
    # 统计概率大于0.1的比例
    high_prob_ratio = (all_probs > 0.1).sum() / all_probs.size
    print(f"  概率>0.1的比例: {high_prob_ratio*100:.2f}%")
    
    print(f"\n缩放后概率分布（缩放因子5.0）:")
    print(f"  最小值: {all_scaled_probs.min():.6f}")
    print(f"  最大值: {all_scaled_probs.max():.6f}")
    print(f"  平均值: {all_scaled_probs.mean():.6f}")
    print(f"  中位数: {np.median(all_scaled_probs):.6f}")
    print(f"  标准差: {all_scaled_probs.std():.6f}")
    
    # 统计缩放后概率为1.0的比例
    max_prob_ratio = (all_scaled_probs == 1.0).sum() / all_scaled_probs.size
    print(f"  缩放后概率=1.0的比例: {max_prob_ratio*100:.2f}%")
    
    # 统计缩放后概率>0.3的比例
    threshold_03_ratio = (all_scaled_probs > 0.3).sum() / all_scaled_probs.size
    print(f"  缩放后概率>0.3的比例: {threshold_03_ratio*100:.2f}%")
    
    return all_probs, all_scaled_probs, all_logits, true_card_counts, predicted_card_counts

def analyze_prediction_accuracy(all_scaled_probs, true_card_counts, predicted_card_counts):
    """分析预测准确率"""
    print("\n" + "="*60)
    print("3. 预测准确率分析")
    print("="*60)
    
    true_card_counts = np.array(true_card_counts)
    predicted_card_counts = np.array(predicted_card_counts)
    
    print(f"\n真实卡牌数统计:")
    print(f"  平均值: {np.mean(true_card_counts):.2f}")
    print(f"  中位数: {np.median(true_card_counts):.2f}")
    print(f"  最小值: {true_card_counts.min()}")
    print(f"  最大值: {true_card_counts.max()}")
    
    print(f"\n预测卡牌数统计（阈值0.3）:")
    print(f"  平均值: {np.mean(predicted_card_counts):.2f}")
    print(f"  中位数: {np.median(predicted_card_counts):.2f}")
    print(f"  最小值: {predicted_card_counts.min()}")
    print(f"  最大值: {predicted_card_counts.max()}")
    
    print(f"\n差异分析:")
    diff = predicted_card_counts - true_card_counts
    print(f"  平均差异: {np.mean(diff):.2f} 张")
    print(f"  中位数差异: {np.median(diff):.2f} 张")
    print(f"  预测过多样本: {(diff > 0).sum()} ({(diff > 0).sum()/len(diff)*100:.1f}%)")
    print(f"  预测过少样本: {(diff < 0).sum()} ({(diff < 0).sum()/len(diff)*100:.1f}%)")
    print(f"  完全匹配样本: {(diff == 0).sum()} ({(diff == 0).sum()/len(diff)*100:.1f}%)")
    
    # 分析预测过多的程度
    over_predictions = diff[diff > 0]
    if len(over_predictions) > 0:
        print(f"\n预测过多分析:")
        print(f"  平均多预测: {np.mean(over_predictions):.2f} 张")
        print(f"  最大多预测: {over_predictions.max()} 张")
        print(f"  多预测>5张的样本: {(over_predictions > 5).sum()} ({(over_predictions > 5).sum()/len(diff)*100:.1f}%)")
        print(f"  多预测>10张的样本: {(over_predictions > 10).sum()} ({(over_predictions > 10).sum()/len(diff)*100:.1f}%)")
    
    # 分析预测过少的程度
    under_predictions = diff[diff < 0]
    if len(under_predictions) > 0:
        print(f"\n预测过少分析:")
        print(f"  平均少预测: {np.mean(under_predictions):.2f} 张")
        print(f"  最大少预测: {under_predictions.min()} 张")

def analyze_prediction_patterns(all_scaled_probs, true_card_counts, sample_indices, dataset):
    """分析模型预测模式（是否总是预测相同的卡牌索引）"""
    print("\n" + "="*60)
    print("4. 模型预测模式分析")
    print("="*60)
    
    # 分析每个样本预测的卡牌索引
    predicted_indices_list = []
    true_indices_list = []
    
    for i, idx in enumerate(sample_indices[:100]):  # 只分析前100个样本
        scaled_probs = all_scaled_probs[i]
        predicted_indices = np.where(scaled_probs > 0.3)[0].tolist()
        predicted_indices_list.append(predicted_indices)
        
        # 获取真实卡牌索引
        _, action_vec, _, _ = dataset[idx]
        true_indices = np.where(action_vec.numpy() > 0.5)[0].tolist()
        true_indices_list.append(true_indices)
    
    # 统计哪些索引最常被预测
    print(f"\n最常被预测的卡牌索引（Top 20）:")
    predicted_index_counts = defaultdict(int)
    for indices in predicted_indices_list:
        for idx in indices:
            predicted_index_counts[int(idx)] += 1
    
    top_predicted = sorted(predicted_index_counts.items(), key=lambda x: x[1], reverse=True)[:20]
    for idx, count in top_predicted:
        print(f"  索引{idx}: {count}次 ({count/len(predicted_indices_list)*100:.1f}%)")
    
    # 分析预测的一致性（是否总是预测相同的索引）
    print(f"\n预测一致性分析:")
    if len(predicted_indices_list) > 0:
        # 计算所有样本预测的索引集合的交集
        if len(predicted_indices_list[0]) > 0:
            common_indices = set(predicted_indices_list[0])
            for indices in predicted_indices_list[1:]:
                common_indices &= set(indices)
            
            print(f"  所有样本都预测的索引数: {len(common_indices)}")
            if len(common_indices) > 0:
                print(f"  这些索引是: {sorted(list(common_indices))[:10]}...")
                print(f"  ⚠️ 问题：模型总是预测相同的卡牌索引，说明模型没有学会根据状态预测")
        
        # 分析预测索引的多样性
        all_predicted_indices = set()
        for indices in predicted_indices_list:
            all_predicted_indices |= set(indices)
        print(f"  预测索引的多样性: {len(all_predicted_indices)} 个不同的索引")
        print(f"  平均每个样本预测: {np.mean([len(indices) for indices in predicted_indices_list]):.2f} 个索引")
    
    # 分析预测索引与真实索引的重叠
    print(f"\n预测索引与真实索引的重叠分析（前100个样本）:")
    overlaps = []
    for i in range(min(100, len(predicted_indices_list))):
        pred_set = set(predicted_indices_list[i])
        true_set = set(true_indices_list[i])
        if len(true_set) > 0:
            overlap = len(pred_set & true_set) / len(true_set)
            overlaps.append(overlap)
    
    if len(overlaps) > 0:
        print(f"  平均重叠率: {np.mean(overlaps):.4f} ({np.mean(overlaps)*100:.2f}%)")
        print(f"  中位数重叠率: {np.median(overlaps):.4f} ({np.median(overlaps)*100:.2f}%)")
        print(f"  完全重叠样本: {(np.array(overlaps) == 1.0).sum()} ({(np.array(overlaps) == 1.0).sum()/len(overlaps)*100:.1f}%)")
        print(f"  无重叠样本: {(np.array(overlaps) == 0.0).sum()} ({(np.array(overlaps) == 0.0).sum()/len(overlaps)*100:.1f}%)")

def analyze_data_quality_issues(dataset, sample_indices):
    """分析数据质量问题"""
    print("\n" + "="*60)
    print("5. 数据质量问题分析")
    print("="*60)
    
    # 检查action_vec编码是否正确
    print(f"\n检查action_vec编码:")
    empty_samples = 0
    invalid_samples = 0
    
    for idx in sample_indices[:1000]:
        state_vec, action_vec, _, _ = dataset[idx]
        card_count = action_vec.sum().item()
        
        if card_count == 0:
            empty_samples += 1
        elif card_count > 27:  # 一副牌最多27张
            invalid_samples += 1
    
    print(f"  空动作样本（card_count=0）: {empty_samples} ({empty_samples/1000*100:.1f}%)")
    print(f"  无效样本（card_count>27）: {invalid_samples} ({invalid_samples/1000*100:.1f}%)")
    
    # 检查state_vec是否包含有效信息
    print(f"\n检查state_vec信息:")
    state_vec_samples = []
    for idx in sample_indices[:100]:
        state_vec, _, _, _ = dataset[idx]
        state_vec_samples.append(state_vec.numpy())
    
    state_vecs = np.array(state_vec_samples)
    # 检查哪些维度总是为0
    always_zero_dims = []
    for dim in range(state_vecs.shape[1]):
        if (state_vecs[:, dim] == 0).all():
            always_zero_dims.append(dim)
    
    print(f"  总是为0的维度数: {len(always_zero_dims)}")
    if len(always_zero_dims) > 0:
        print(f"  这些维度是: {always_zero_dims[:20]}...")
        print(f"  ⚠️ 问题：部分状态维度总是为0，可能影响模型学习")

def generate_summary_report(card_counts, all_probs, all_scaled_probs, true_card_counts, 
                           predicted_card_counts, output_file="training_logs/data_quality_analysis_solution_b.json"):
    """生成总结报告"""
    print("\n" + "="*60)
    print("6. 总结报告")
    print("="*60)
    
    # 计算关键指标
    avg_true_cards = np.mean(true_card_counts)
    avg_pred_cards = np.mean(predicted_card_counts)
    avg_prob = all_probs.mean()
    median_prob = np.median(all_probs)
    zero_prob_ratio = (all_probs == 0).sum() / all_probs.size
    max_prob_ratio = (all_scaled_probs == 1.0).sum() / all_scaled_probs.size
    
    # 完全匹配率
    diff = np.array(predicted_card_counts) - np.array(true_card_counts)
    exact_match_rate = (diff == 0).sum() / len(diff)
    
    report = {
        "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model": "bc_model_v1_epoch_120.pth (方案B)",
        "key_metrics": {
            "avg_true_cards": float(avg_true_cards),
            "avg_pred_cards": float(avg_pred_cards),
            "avg_prob": float(avg_prob),
            "median_prob": float(median_prob),
            "zero_prob_ratio": float(zero_prob_ratio),
            "max_prob_ratio": float(max_prob_ratio),
            "exact_match_rate": float(exact_match_rate)
        },
        "issues": []
    }
    
    # 识别问题
    if avg_pred_cards > avg_true_cards * 2:
        report["issues"].append({
            "type": "over_prediction",
            "severity": "high",
            "description": f"预测卡牌数过多：平均预测{avg_pred_cards:.2f}张，真实{avg_true_cards:.2f}张",
            "suggestion": "降低缩放因子或提高阈值"
        })
    
    if zero_prob_ratio > 0.9:
        report["issues"].append({
            "type": "low_probability",
            "severity": "high",
            "description": f"模型输出概率过低：{zero_prob_ratio*100:.1f}%的概率为0",
            "suggestion": "检查损失函数和训练参数"
        })
    
    if max_prob_ratio > 0.1:
        report["issues"].append({
            "type": "scaling_issue",
            "severity": "medium",
            "description": f"缩放因子过大：{max_prob_ratio*100:.1f}%的概率被缩放到1.0",
            "suggestion": "降低缩放因子"
        })
    
    if exact_match_rate < 0.01:
        report["issues"].append({
            "type": "exact_match_failure",
            "severity": "critical",
            "description": f"完全匹配率极低：{exact_match_rate*100:.2f}%",
            "suggestion": "需要根本性改进：检查数据质量、损失函数、模型架构"
        })
    
    # 保存报告
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n报告已保存到: {output_file}")
    print(f"\n关键发现:")
    for issue in report["issues"]:
        print(f"  [{issue['severity'].upper()}] {issue['type']}: {issue['description']}")
        print(f"    建议: {issue['suggestion']}")
    
    return report

if __name__ == "__main__":
    print("="*60)
    print("方案B数据质量分析")
    print("="*60)
    print()
    
    # 加载模型
    model_path = "models/bc_model_v1_epoch_120.pth"
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    print(f"加载模型: {model_path}")
    model = GuandanPolicyNet(
        input_dim=512,
        hidden_dim=256,
        output_dim=512,
        dropout_rate=0.01,
        enable_strategy_head=False
    ).to(device)
    
    checkpoint = torch.load(model_path, map_location=device, weights_only=False)
    if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
        model.load_state_dict(checkpoint['model_state_dict'])
    else:
        model.load_state_dict(checkpoint)
    model.eval()
    print("模型加载完成")
    
    # 加载数据
    print("\n加载训练数据...")
    parser = ReplayParser("game_records")
    replays = parser.load_replays()
    raw_data = parser.extract_training_data(replays)
    dataset = GuandanDataset(raw_data)
    print(f"数据加载完成，共 {len(dataset)} 个样本")
    
    # 分析
    card_counts, action_vec_samples, sample_indices = analyze_action_vec_distribution(dataset, max_samples=1000)
    all_probs, all_scaled_probs, all_logits, true_card_counts, predicted_card_counts = \
        analyze_model_output_distribution(model, dataset, device, sample_indices, max_samples=1000)
    analyze_prediction_accuracy(all_scaled_probs, true_card_counts, predicted_card_counts)
    analyze_prediction_patterns(all_scaled_probs, true_card_counts, sample_indices, dataset)
    analyze_data_quality_issues(dataset, sample_indices)
    report = generate_summary_report(card_counts, all_probs, all_scaled_probs, 
                                    true_card_counts, predicted_card_counts)
    
    print("\n" + "="*60)
    print("分析完成")
    print("="*60)

