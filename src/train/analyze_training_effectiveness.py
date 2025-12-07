# -*- coding: utf-8 -*-
"""
分析预训练效果
对比不同数据量下的模型表现
"""

import sys
import os
import torch
import numpy as np
import json
from datetime import datetime

# **修复**：设置Windows控制台编码为UTF-8
if sys.platform == 'win32':
    try:
        import io
        # 只在stdout/stderr还没有被包装时进行包装
        if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        if not isinstance(sys.stderr, io.TextIOWrapper) or sys.stderr.encoding != 'utf-8':
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        # 如果已经是TextIOWrapper或buffer不存在，跳过
        pass

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.rl_agent.model import GuandanPolicyNet
from src.knowledge_processor.replay_parser import ReplayParser
from src.train.pretrain import GuandanDataset
from torch.utils.data import DataLoader


def analyze_training_effectiveness():
    """分析预训练效果"""
    print("="*60)
    print("预训练效果分析")
    print("="*60)
    
    # 1. 检查训练数据
    parser = ReplayParser("game_records")
    replays = parser.load_replays()
    raw_data = parser.extract_training_data(replays)
    
    print(f"\n当前训练数据:")
    print(f"  对局文件数: {len(replays)} 个")
    print(f"  训练样本数: {len(raw_data)} 个")
    print(f"  平均每局样本数: {len(raw_data) / len(replays) if len(replays) > 0 else 0:.1f} 个")
    
    # 2. 检查模型
    model_path = "models/bc_model_v1.pth"
    if not os.path.exists(model_path):
        print(f"\n[ERROR] 模型文件不存在: {model_path}")
        return
    
    model_size = os.path.getsize(model_path) / (1024 * 1024)
    model_time = os.path.getmtime(model_path)
    from datetime import datetime
    model_time_str = datetime.fromtimestamp(model_time).strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"\n模型信息:")
    print(f"  模型文件: {model_path}")
    print(f"  模型大小: {model_size:.2f} MB")
    print(f"  最后修改: {model_time_str}")
    
    # 3. 加载模型并评估
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = GuandanPolicyNet(input_dim=512, hidden_dim=256, output_dim=512).to(device)
    
    try:
        model.load_state_dict(torch.load(model_path, map_location=device))
        print(f"  [OK] 模型加载成功")
    except Exception as e:
        print(f"  [ERROR] 模型加载失败: {e}")
        return
    
    model.eval()
    
    # 4. 评估指标
    dataset = GuandanDataset(raw_data)
    dataloader = DataLoader(dataset, batch_size=32, shuffle=False)
    
    total_samples = 0
    correct_predictions = 0
    total_cards = 0
    card_match = 0
    predicted_cards = 0
    
    # 分析预测分布
    prediction_stats = {
        "over_predict": 0,
        "under_predict": 0,
        "exact_match": 0,
        "card_count_diff": []
    }
    
    # **修复**：使用与推理代码相同的设置
    # 使用 model.get_action() 方法，它会自动应用缩放因子和阈值
    # 当前配置：阈值0.3，缩放因子5.0（根据2025-12-07评估结果进一步优化）
    prediction_threshold = 0.3
    
    # 收集所有概率值用于分析（原始概率，用于分析）
    all_probs_list = []
    all_scaled_probs_list = []
    
    with torch.no_grad():
        for states, actions in dataloader:
            states = states.to(device)
            actions = actions.to(device)
            
            # 获取原始概率（用于分析）
            logits = model(states)
            probs = torch.sigmoid(logits)
            all_probs_list.append(probs.cpu())
            
            # 使用 get_action 方法（自动应用缩放和阈值，与推理代码一致）
            predictions_list = []
            scaled_probs_list = []
            for i in range(len(states)):
                state = states[i:i+1]  # 保持batch维度
                # 获取缩放后的概率（用于分析）
                with torch.no_grad():
                    logits_single = model(state)
                    probs_single = torch.sigmoid(logits_single)
                    scaled_probs = probs_single * 5.0  # 与推理代码一致的缩放因子（已进一步调整为5.0）
                    scaled_probs = torch.clamp(scaled_probs, 0, 1)
                    scaled_probs_list.append(scaled_probs.cpu())
                
                # 使用 get_action 方法（与推理代码一致）
                action = model.get_action(state, deterministic=True, threshold=prediction_threshold)
                if action.ndim > 1:
                    action = action.flatten()
                predictions_list.append(torch.from_numpy(action).float())
            
            predictions = torch.stack(predictions_list).to(device)
            all_scaled_probs_list.append(torch.cat(scaled_probs_list, dim=0))
            
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
    
    # 5. 输出结果
    exact_accuracy = correct_predictions / total_samples if total_samples > 0 else 0
    card_accuracy = card_match / total_cards if total_cards > 0 else 0
    avg_pred_count = predicted_cards / total_samples if total_samples > 0 else 0
    avg_true_count = sum(prediction_stats["card_count_diff"]) / len(prediction_stats["card_count_diff"]) if prediction_stats["card_count_diff"] else 0
    
    # 计算概率统计（原始概率和缩放后概率）
    if all_probs_list:
        all_probs = torch.cat(all_probs_list, dim=0)
        prob_mean = all_probs.mean().item()
        prob_median = all_probs.median().item()
        prob_min = all_probs.min().item()
        prob_max = all_probs.max().item()
    else:
        prob_mean = prob_median = prob_min = prob_max = 0
    
    if all_scaled_probs_list:
        all_scaled_probs = torch.cat(all_scaled_probs_list, dim=0)
        scaled_prob_mean = all_scaled_probs.mean().item()
        scaled_prob_median = all_scaled_probs.median().item()
        scaled_prob_min = all_scaled_probs.min().item()
        scaled_prob_max = all_scaled_probs.max().item()
    else:
        scaled_prob_mean = scaled_prob_median = scaled_prob_min = scaled_prob_max = 0
    
    print(f"\n" + "="*60)
    print(f"模型评估结果（阈值{prediction_threshold}，缩放因子5.0）")
    print("="*60)
    print(f"总样本数: {total_samples}")
    print(f"完全匹配样本数: {correct_predictions}")
    print(f"完全匹配准确率: {exact_accuracy:.2%}")
    print(f"卡牌级别准确率: {card_accuracy:.2%}")
    print(f"平均预测卡牌数: {avg_pred_count:.2f}")
    print(f"\n模型输出概率分析:")
    print(f"  原始概率范围: [{prob_min:.4f}, {prob_max:.4f}]")
    print(f"  原始概率平均: {prob_mean:.4f}")
    print(f"  原始概率中位数: {prob_median:.4f}")
    print(f"  缩放后概率范围: [{scaled_prob_min:.4f}, {scaled_prob_max:.4f}]")
    print(f"  缩放后概率平均: {scaled_prob_mean:.4f}")
    print(f"  缩放后概率中位数: {scaled_prob_median:.4f}")
    
    print(f"\n预测分布分析:")
    print(f"  完全匹配: {prediction_stats['exact_match']} ({prediction_stats['exact_match']/total_samples*100:.1f}%)")
    print(f"  预测过多: {prediction_stats['over_predict']} ({prediction_stats['over_predict']/total_samples*100:.1f}%)")
    print(f"  预测过少: {prediction_stats['under_predict']} ({prediction_stats['under_predict']/total_samples*100:.1f}%)")
    
    if prediction_stats["card_count_diff"]:
        avg_diff = sum(prediction_stats["card_count_diff"]) / len(prediction_stats["card_count_diff"])
        print(f"  平均卡牌数量差异: {avg_diff:.2f}")
    
    # 6. 历史对比
    print(f"\n" + "="*60)
    print("历史对比")
    print("="*60)
    
    print(f"\n数据量变化:")
    print(f"  初始: 10个样本 (1个对局)")
    print(f"  中期: 252个样本 (23个对局)")
    print(f"  现在: {len(raw_data)}个样本 ({len(replays)}个对局)")
    
    print(f"\n准确率变化:")
    print(f"  初始 (10样本): 完全匹配 59.41%, 卡牌级别 99.78%")
    print(f"  中期 (252样本): 完全匹配 23.81%, 卡牌级别 99.52%")
    print(f"  现在 ({len(raw_data)}样本): 完全匹配 {exact_accuracy:.2%}, 卡牌级别 {card_accuracy:.2%}")
    
    # 7. 分析
    print(f"\n" + "="*60)
    print("效果分析")
    print("="*60)
    
    if exact_accuracy < 0.1:
        print(f"\n[WARNING] 完全匹配准确率很低（{exact_accuracy:.2%}）")
        print(f"  可能原因:")
        print(f"  1. 模型输出概率值整体偏低（平均{prob_mean:.4f}）")
        print(f"  2. 预测过少问题严重（{prediction_stats['under_predict']/total_samples*100:.1f}%的样本预测不足）")
        print(f"  3. 需要调整模型输出（概率缩放）或进一步降低阈值")
        print(f"  4. 可能需要重新训练，调整训练参数")
    elif exact_accuracy < 0.3:
        print(f"\n[INFO] 完全匹配准确率一般（{exact_accuracy:.2%}）")
        print(f"  建议:")
        print(f"  1. 增加训练轮数到30-50轮")
        print(f"  2. 调整学习率（尝试0.0003）")
        print(f"  3. 使用学习率衰减")
    else:
        print(f"\n[OK] 完全匹配准确率良好（{exact_accuracy:.2%}）")
    
    if card_accuracy > 0.99:
        print(f"\n[EXCELLENT] 卡牌级别准确率优秀（{card_accuracy:.2%}）")
        print(f"  说明模型能正确识别卡牌，方向正确！")
    
    if prediction_stats["under_predict"] > prediction_stats["over_predict"] * 2:
        print(f"\n[WARNING] 模型严重倾向于预测过少（{prediction_stats['under_predict']/total_samples*100:.1f}%）")
        print(f"  当前设置: 缩放因子5.0，阈值{prediction_threshold}")
        print(f"  建议:")
        print(f"  1. 进一步降低预测阈值（当前{prediction_threshold}，尝试0.05或0.01）")
        print(f"  2. 增加概率缩放因子（当前10.0，尝试15.0或20.0）")
        print(f"  3. 重新训练，调整训练参数（减少Dropout比率，调整损失函数）")
    
    # 8. 建议
    print(f"\n" + "="*60)
    print("改进建议")
    print("="*60)
    
    print(f"\n1. 进一步降低预测阈值（如果预测过少）")
    print(f"   - 当前: {prediction_threshold}（已优化）")
    print(f"   - 如果预测过少，尝试: 0.05 或 0.01")
    print(f"   - 预期效果: 完全匹配准确率可能提升5-10%")
    
    print(f"\n2. 调整概率缩放因子（如果预测过少或过多）")
    print(f"   - 当前: 7.0（已调整，从10.0降低）")
    print(f"   - 如果预测过少，尝试: 10.0 或 15.0")
    print(f"   - 如果预测过多，尝试: 5.0 或 6.0")
    print(f"   - 修改 src/rl_agent/model.py 中的 get_action 方法")
    print(f"   - 预期效果: 完全匹配准确率可能提升10-20%")
    
    print(f"\n3. 重新训练模型（长期方案）")
    print(f"   - 数据量: {len(raw_data)}个样本（充足）")
    print(f"   - 训练轮数: 50轮（已完成）")
    print(f"   - 减少Dropout比率: 0.2 → 0.1")
    print(f"   - 调整学习率: 0.0003 → 0.0005")
    print(f"   - 调整损失函数: 增加对预测过少的惩罚")
    
    print(f"\n4. 数据质量")
    print(f"   - 当前数据量充足（{len(raw_data)}个样本）")
    print(f"   - 建议验证数据质量")
    print(f"   - 确保选择获胜玩家的数据")
    
    print(f"\n" + "="*60)
    
    # 9. 保存评估结果到文件
    os.makedirs("training_logs", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    eval_log_path = f"training_logs/evaluation_log_{timestamp}.json"
    
    eval_result = {
        "timestamp": datetime.now().isoformat(),
        "data_info": {
            "total_games": len(replays),
            "total_samples": len(raw_data),
            "avg_samples_per_game": len(raw_data) / len(replays) if len(replays) > 0 else 0
        },
        "model_info": {
            "model_path": model_path,
            "model_size_mb": model_size,
            "last_modified": model_time_str
        },
        "evaluation_results": {
            "prediction_threshold": prediction_threshold,
            "scale_factor": 5.0,
            "total_samples": total_samples,
            "exact_match_samples": correct_predictions,
            "exact_accuracy": exact_accuracy,
            "card_accuracy": card_accuracy,
            "avg_predicted_cards": avg_pred_count,
            "probability_stats": {
                "raw_min": prob_min,
                "raw_max": prob_max,
                "raw_mean": prob_mean,
                "raw_median": prob_median,
                "scaled_min": scaled_prob_min,
                "scaled_max": scaled_prob_max,
                "scaled_mean": scaled_prob_mean,
                "scaled_median": scaled_prob_median
            },
            "prediction_distribution": {
                "exact_match": prediction_stats['exact_match'],
                "exact_match_pct": prediction_stats['exact_match']/total_samples*100,
                "over_predict": prediction_stats['over_predict'],
                "over_predict_pct": prediction_stats['over_predict']/total_samples*100,
                "under_predict": prediction_stats['under_predict'],
                "under_predict_pct": prediction_stats['under_predict']/total_samples*100,
                "avg_card_count_diff": sum(prediction_stats["card_count_diff"]) / len(prediction_stats["card_count_diff"]) if prediction_stats["card_count_diff"] else 0
            }
        },
        "historical_comparison": {
            "initial": {"samples": 10, "games": 1, "exact_accuracy": 0.5941, "card_accuracy": 0.9978},
            "mid": {"samples": 252, "games": 23, "exact_accuracy": 0.2381, "card_accuracy": 0.9952},
            "current": {"samples": len(raw_data), "games": len(replays), "exact_accuracy": exact_accuracy, "card_accuracy": card_accuracy}
        }
    }
    
    with open(eval_log_path, 'w', encoding='utf-8') as f:
        json.dump(eval_result, f, indent=2, ensure_ascii=False)
    
    print(f"\n[INFO] 评估结果已保存到: {eval_log_path}")


if __name__ == "__main__":
    analyze_training_effectiveness()

