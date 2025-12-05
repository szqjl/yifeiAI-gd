# -*- coding: utf-8 -*-
"""
对比训练效果脚本
对比不同训练阶段的模型效果
"""

import sys
import os
import torch
import numpy as np

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.rl_agent.model import GuandanPolicyNet
from src.knowledge_processor.replay_parser import ReplayParser
from src.train.pretrain import GuandanDataset
from torch.utils.data import DataLoader


def analyze_training_progress():
    """分析训练进度"""
    print("="*60)
    print("训练效果对比分析")
    print("="*60)
    
    # 1. 检查训练数据
    parser = ReplayParser("game_records")
    replays = parser.load_replays()
    raw_data = parser.extract_training_data(replays)
    
    print(f"\n当前训练数据统计:")
    print(f"  对局文件数: {len(replays)} 个")
    print(f"  训练样本数: {len(raw_data)} 个")
    
    # 统计每个对局的样本数
    samples_per_replay = {}
    for replay in replays:
        player_id = replay.get('player_id', 'unknown')
        action_count = len(replay.get('actions', []))
        if player_id not in samples_per_replay:
            samples_per_replay[player_id] = []
        samples_per_replay[player_id].append(action_count)
    
    print(f"\n各玩家数据分布:")
    for player_id in sorted(samples_per_replay.keys(), key=lambda x: (isinstance(x, str), x)):
        counts = samples_per_replay[player_id]
        total = sum(counts)
        avg = total / len(counts) if counts else 0
        print(f"  玩家 {player_id}: {len(counts)} 个对局, {total} 个样本, 平均 {avg:.1f} 个/局")
    
    # 2. 评估当前模型
    model_path = "models/bc_model_v1.pth"
    if not os.path.exists(model_path):
        print(f"\n[ERROR] 模型文件不存在: {model_path}")
        return
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = GuandanPolicyNet(input_dim=512, hidden_dim=256, output_dim=512).to(device)
    
    try:
        model.load_state_dict(torch.load(model_path, map_location=device))
        print(f"\n[OK] 模型加载成功")
    except Exception as e:
        print(f"\n[ERROR] 模型加载失败: {e}")
        return
    
    model.eval()
    
    # 3. 评估指标
    dataset = GuandanDataset(raw_data)
    dataloader = DataLoader(dataset, batch_size=32, shuffle=False)
    
    total_samples = 0
    correct_predictions = 0
    total_cards = 0
    card_match = 0
    predicted_cards = 0
    
    # 分析预测分布
    prediction_stats = {
        "over_predict": 0,  # 预测过多
        "under_predict": 0,  # 预测过少
        "exact_match": 0,    # 完全匹配
        "card_count_diff": []  # 卡牌数量差异
    }
    
    with torch.no_grad():
        for states, actions in dataloader:
            states = states.to(device)
            actions = actions.to(device)
            
            logits = model(states)
            probs = torch.sigmoid(logits)
            predictions = (probs > 0.5).float()
            
            # 完全匹配
            exact_match = (predictions == actions).all(dim=1)
            correct_predictions += exact_match.sum().item()
            total_samples += len(states)
            
            # 卡牌级别
            batch_card_match = (predictions == actions).sum().item()
            card_match += batch_card_match
            total_cards += actions.numel()
            predicted_cards += predictions.sum().item()
            
            # 分析预测数量
            for i in range(len(states)):
                true_count = actions[i].sum().item()
                pred_count = predictions[i].sum().item()
                diff = pred_count - true_count
                prediction_stats["card_count_diff"].append(diff)
                
                if diff > 0:
                    prediction_stats["over_predict"] += 1
                elif diff < 0:
                    prediction_stats["under_predict"] += 1
                else:
                    prediction_stats["exact_match"] += 1
    
    # 4. 输出结果
    exact_accuracy = correct_predictions / total_samples if total_samples > 0 else 0
    card_accuracy = card_match / total_cards if total_cards > 0 else 0
    avg_pred_count = predicted_cards / total_samples if total_samples > 0 else 0
    avg_true_count = sum(prediction_stats["card_count_diff"]) / len(prediction_stats["card_count_diff"]) if prediction_stats["card_count_diff"] else 0
    
    print(f"\n" + "="*60)
    print("模型评估结果")
    print("="*60)
    print(f"总样本数: {total_samples}")
    print(f"完全匹配样本数: {correct_predictions}")
    print(f"完全匹配准确率: {exact_accuracy:.2%}")
    print(f"卡牌级别准确率: {card_accuracy:.2%}")
    print(f"平均预测卡牌数: {avg_pred_count:.2f}")
    
    print(f"\n预测分布分析:")
    print(f"  完全匹配: {prediction_stats['exact_match']} ({prediction_stats['exact_match']/total_samples*100:.1f}%)")
    print(f"  预测过多: {prediction_stats['over_predict']} ({prediction_stats['over_predict']/total_samples*100:.1f}%)")
    print(f"  预测过少: {prediction_stats['under_predict']} ({prediction_stats['under_predict']/total_samples*100:.1f}%)")
    
    if prediction_stats["card_count_diff"]:
        avg_diff = sum(prediction_stats["card_count_diff"]) / len(prediction_stats["card_count_diff"])
        print(f"  平均卡牌数量差异: {avg_diff:.2f}")
    
    # 5. 对比分析
    print(f"\n" + "="*60)
    print("效果对比")
    print("="*60)
    
    print(f"\n数据量变化:")
    print(f"  之前: 10个样本 (1个对局)")
    print(f"  现在: {len(raw_data)}个样本 ({len(replays)}个对局)")
    print(f"  提升: {len(raw_data)/10:.1f}倍")
    
    print(f"\n准确率变化:")
    print(f"  之前: 完全匹配 59.41%, 卡牌级别 99.78%")
    print(f"  现在: 完全匹配 {exact_accuracy:.2%}, 卡牌级别 {card_accuracy:.2%}")
    
    exact_change = exact_accuracy - 0.5941
    card_change = card_accuracy - 0.9978
    
    if exact_change > 0:
        print(f"  完全匹配: 提升 {exact_change:.2%} [OK]")
    else:
        print(f"  完全匹配: 下降 {abs(exact_change):.2%} [WARNING]")
    
    if card_change > 0:
        print(f"  卡牌级别: 提升 {card_change:.2%} [OK]")
    else:
        print(f"  卡牌级别: 下降 {abs(card_change):.2%} (但仍在高位)")
    
    # 6. 分析原因
    print(f"\n" + "="*60)
    print("原因分析")
    print("="*60)
    
    if exact_accuracy < 0.5:
        print(f"\n[WARNING] 完全匹配准确率较低，可能原因:")
        print(f"  1. 测试数据更复杂（从101个增加到252个样本）")
        print(f"  2. 数据多样性增加，模型需要适应更多情况")
        print(f"  3. 模型可能过拟合训练数据")
        print(f"  4. 需要更多训练轮数或调整超参数")
    
    if prediction_stats["over_predict"] > prediction_stats["under_predict"]:
        print(f"\n[INFO] 模型倾向于预测过多卡牌")
        print(f"  建议: 降低预测阈值（从0.5降到0.4）或调整损失函数")
    elif prediction_stats["under_predict"] > prediction_stats["over_predict"]:
        print(f"\n[INFO] 模型倾向于预测过少卡牌")
        print(f"  建议: 提高预测阈值（从0.5升到0.6）或调整损失函数")
    
    # 7. 改进建议
    print(f"\n" + "="*60)
    print("改进建议")
    print("="*60)
    
    if exact_accuracy < 0.5:
        print(f"  1. 增加训练轮数（当前20轮，建议30-50轮）")
        print(f"  2. 调整学习率（当前0.0005，尝试0.0003或0.0001）")
        print(f"  3. 使用学习率衰减策略")
        print(f"  4. 增加正则化（Dropout或L2正则化）")
        print(f"  5. 使用验证集监控过拟合")
    
    if len(raw_data) < 500:
        print(f"  6. 继续收集训练数据（当前{len(raw_data)}个，建议至少500个）")
    
    print(f"\n" + "="*60)


if __name__ == "__main__":
    analyze_training_progress()

