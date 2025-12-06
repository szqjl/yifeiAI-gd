# -*- coding: utf-8 -*-
"""
模型评估脚本
用于评估训练好的模型效果
"""

import sys
import os
import torch
import numpy as np

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


def evaluate_model(model_path="models/bc_model_v1.pth", data_dir="game_records"):
    """
    评估模型效果
    
    Args:
        model_path: 模型文件路径
        data_dir: 测试数据目录
    """
    print("="*60)
    print("模型评估")
    print("="*60)
    
    # 1. 检查模型文件
    if not os.path.exists(model_path):
        print(f"[ERROR] 模型文件不存在: {model_path}")
        return
    
    model_size = os.path.getsize(model_path) / (1024 * 1024)  # MB
    print(f"[OK] 模型文件: {model_path}")
    print(f"[OK] 模型大小: {model_size:.2f} MB")
    
    # 2. 加载模型
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[OK] 使用设备: {device}")
    
    model = GuandanPolicyNet(input_dim=512, hidden_dim=256, output_dim=512).to(device)
    try:
        model.load_state_dict(torch.load(model_path, map_location=device))
        print("[OK] 模型加载成功")
    except Exception as e:
        print(f"[ERROR] 模型加载失败: {e}")
        return
    
    model.eval()
    
    # 3. 加载测试数据
    parser = ReplayParser(data_dir)
    replays = parser.load_replays()
    raw_data = parser.extract_training_data(replays)
    
    if len(raw_data) == 0:
        print(f"[ERROR] 没有找到测试数据: {data_dir}")
        return
    
    print(f"[OK] 测试数据: {len(raw_data)} 个样本")
    
    # 4. 评估指标
    dataset = GuandanDataset(raw_data)
    dataloader = DataLoader(dataset, batch_size=32, shuffle=False)
    
    total_samples = 0
    correct_predictions = 0
    total_cards = 0
    predicted_cards = 0
    card_match = 0
    
    with torch.no_grad():
        for states, actions in dataloader:
            states = states.to(device)
            actions = actions.to(device)
            
            # 模型预测
            # **优化**: 使用get_action方法，包含概率缩放优化
            # 这样评估结果与推理时一致
            prediction_threshold = 0.5  # 最优阈值（基于自动测试）
            
            # 批量处理，提高效率
            predictions_list = []
            for i in range(len(states)):
                state = states[i:i+1]  # 保持batch维度
                action = model.get_action(state, deterministic=True, threshold=prediction_threshold)
                # get_action返回numpy数组，需要转换为tensor
                # 确保action是一维数组
                if action.ndim > 1:
                    action = action.flatten()
                predictions_list.append(torch.from_numpy(action).float())
            predictions = torch.stack(predictions_list).to(device)
            
            # 确保predictions和actions维度一致
            if predictions.shape != actions.shape:
                print(f"[WARNING] 维度不匹配: predictions {predictions.shape} vs actions {actions.shape}")
                # 调整维度
                if predictions.shape[1] != actions.shape[1]:
                    min_dim = min(predictions.shape[1], actions.shape[1])
                    predictions = predictions[:, :min_dim]
                    actions = actions[:, :min_dim]
            
            # 计算准确率（完全匹配）
            exact_match = (predictions == actions).all(dim=1)
            correct_predictions += exact_match.sum().item()
            total_samples += len(states)
            
            # 计算卡牌级别的准确率
            batch_card_match = (predictions == actions).sum().item()
            card_match += batch_card_match
            total_cards += actions.numel()
            predicted_cards += predictions.sum().item()
            
            # 调试信息（前几个样本）
            if total_samples <= 3:
                for i in range(len(states)):
                    true_count = actions[i].sum().item()
                    pred_count = predictions[i].sum().item()
                    print(f"\n样本 {total_samples + i + 1}:")
                    print(f"  真实动作卡牌数: {true_count:.0f}")
                    print(f"  预测动作卡牌数: {pred_count:.0f}")
                    print(f"  匹配: {true_count == pred_count}")
    
    # 5. 输出结果
    print("\n" + "="*60)
    print("评估结果")
    print("="*60)
    
    exact_accuracy = correct_predictions / total_samples if total_samples > 0 else 0
    card_accuracy = card_match / total_cards if total_cards > 0 else 0
    
    print(f"总样本数: {total_samples}")
    print(f"完全匹配样本数: {correct_predictions}")
    print(f"完全匹配准确率: {exact_accuracy:.2%}")
    print(f"卡牌级别准确率: {card_accuracy:.2%}")
    print(f"平均预测卡牌数: {predicted_cards / total_samples if total_samples > 0 else 0:.2f}")
    
    # 6. 分析
    print("\n" + "="*60)
    print("分析")
    print("="*60)
    
    if exact_accuracy > 0.8:
        print("[EXCELLENT] 模型表现优秀！完全匹配准确率超过80%")
    elif exact_accuracy > 0.5:
        print("[WARNING] 模型表现一般，完全匹配准确率在50%-80%之间")
        print("   建议：增加训练数据或调整超参数")
    else:
        print("[ERROR] 模型表现较差，完全匹配准确率低于50%")
        print("   建议：")
        print("   1. 检查训练数据质量")
        print("   2. 增加训练数据量（至少100个对局）")
        print("   3. 增加训练轮数（10-20轮）")
        print("   4. 调整学习率（尝试0.0005）")
    
    if card_accuracy > 0.7:
        print("[OK] 卡牌级别准确率良好，模型能正确识别大部分卡牌")
    else:
        print("[WARNING] 卡牌级别准确率较低，模型可能过度预测或预测不足")
    
    # 7. 建议
    print("\n" + "="*60)
    print("改进建议")
    print("="*60)
    
    if total_samples < 100:
        print(f"[WARNING] 训练数据量较少（{total_samples}个样本）")
        print("   建议收集至少100个对局（约500-2000个训练样本）")
    
    if exact_accuracy < 0.5:
        print("   1. 增加训练数据量")
        print("   2. 增加训练轮数（10-20轮）")
        print("   3. 调整学习率（0.0005-0.001）")
        print("   4. 检查数据质量（确保选择获胜玩家）")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="评估训练好的模型")
    parser.add_argument("--model", default="models/bc_model_v1.pth", help="模型文件路径")
    parser.add_argument("--data", default="game_records", help="测试数据目录")
    args = parser.parse_args()
    
    evaluate_model(args.model, args.data)

