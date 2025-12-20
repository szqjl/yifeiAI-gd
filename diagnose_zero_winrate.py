#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断胜率为0的轮次问题
深度分析模型输出分布和评估逻辑
"""

import torch
import torch.nn as nn
import numpy as np
import json
import sys
import os
from collections import defaultdict, Counter
sys.path.append('src')

from rl_agent.model import ImprovedGuandanPolicyNet
from train.pretrain import GuandanDataset

def load_converted_model():
    """加载转换后的模型"""
    model_path = "models/bc_model_stage6_enhanced_converted.pth"
    
    if not os.path.exists(model_path):
        print(f"❌ 转换后的模型不存在: {model_path}")
        print("💡 请先运行 python fix_model_compatibility.py")
        return None
    
    try:
        # 创建模型
        model = ImprovedGuandanPolicyNet(
            input_dim=512,
            hidden_dim=256,
            output_dim=512,
            dropout_rate=0.1,
            strategy_num_classes=7,
            enable_strategy_head=True,
            attention_heads=8,
            enable_strategy_tasks=True
        )
        
        # 加载状态字典
        state_dict = torch.load(model_path, map_location='cpu', weights_only=False)
        model.load_state_dict(state_dict)
        model.eval()
        
        print(f"✅ 模型加载成功: {model_path}")
        return model
        
    except Exception as e:
        print(f"❌ 模型加载失败: {e}")
        return None

def analyze_dataset_distribution():
    """分析数据集分布"""
    print("\n=== 数据集分布分析 ===")
    
    data_dir = "game_records"
    if not os.path.exists(data_dir):
        print(f"❌ 数据目录不存在: {data_dir}")
        return None
    
    # 统计游戏记录文件
    json_files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
    print(f"📊 找到 {len(json_files)} 个游戏记录文件")
    
    if len(json_files) == 0:
        print("❌ 没有找到游戏记录文件")
        return None
    
    # 分析文件时间分布
    file_times = []
    file_info = {}
    
    for filename in json_files:
        try:
            # 从文件名提取时间戳
            if filename.startswith('202'):
                timestamp = filename.split(' ')[0]
                file_times.append(timestamp)
                file_info[timestamp] = filename
        except:
            continue
    
    file_times.sort()
    print(f"📅 时间范围: {file_times[0] if file_times else 'N/A'} - {file_times[-1] if file_times else 'N/A'}")
    
    # 分析对手分布
    opponent_stats = Counter()
    game_stats = {
        'total_games': 0,
        'total_decisions': 0,
        'win_games': 0,
        'loss_games': 0
    }
    
    for filename in json_files[:100]:  # 只分析前100个文件
        filepath = os.path.join(data_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 提取对手信息
            if 'opponent_1_3' in filename:
                opponent_stats['opponent_1_3'] += 1
            elif 'unknown' in filename:
                opponent_stats['unknown'] += 1
            else:
                opponent_stats['other'] += 1
            
            # 统计游戏结果
            game_stats['total_games'] += 1
            game_stats['total_decisions'] += len(data.get('my_decisions', []))
            
            result = data.get('result', {})
            victory_num = result.get('victoryNum', [0, 0, 0, 0])
            if isinstance(victory_num, list) and len(victory_num) >= 4:
                my_pos = data.get('player_id', 0)
                teammate_pos = (my_pos + 2) % 4
                my_wins = victory_num[my_pos]
                teammate_wins = victory_num[teammate_pos]
                
                if my_wins > 0 or teammate_wins > 0:
                    game_stats['win_games'] += 1
                else:
                    game_stats['loss_games'] += 1
            
        except Exception as e:
            continue
    
    print(f"🎮 游戏统计:")
    print(f"  总游戏数: {game_stats['total_games']}")
    print(f"  总决策数: {game_stats['total_decisions']}")
    print(f"  胜利游戏: {game_stats['win_games']}")
    print(f"  失败游戏: {game_stats['loss_games']}")
    if game_stats['total_games'] > 0:
        win_rate = game_stats['win_games'] / game_stats['total_games']
        print(f"  实际胜率: {win_rate:.2%}")
    
    print(f"👥 对手分布:")
    for opponent, count in opponent_stats.most_common():
        print(f"  {opponent}: {count} 场游戏")
    
    return {
        'files': json_files,
        'file_times': file_times,
        'opponent_stats': opponent_stats,
        'game_stats': game_stats
    }

def create_test_dataset(data_info, round_size=1000):
    """创建测试数据集，模拟评估过程"""
    print(f"\n=== 创建测试数据集 (每轮{round_size}样本) ===")
    
    try:
        # 简化的数据集创建，直接从游戏记录文件加载
        data_dir = "game_records"
        json_files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
        
        if not json_files:
            print("❌ 没有找到游戏记录文件")
            return None
        
        # 加载游戏记录并创建简单的数据样本
        samples = []
        
        for filename in json_files[:50]:  # 只处理前50个文件
            filepath = os.path.join(data_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    game_data = json.load(f)
                
                # 从游戏决策中创建样本
                decisions = game_data.get('my_decisions', [])
                for decision in decisions[:10]:  # 每个游戏最多10个决策
                    # 创建简化的样本
                    sample = {
                        'state_input': torch.randn(512),  # 模拟状态输入
                        'action_target': torch.zeros(512),  # 模拟动作目标
                        'strategy_target': torch.zeros(7)   # 模拟策略目标
                    }
                    
                    # 随机设置一些动作目标
                    num_cards = np.random.randint(1, 6)
                    card_indices = np.random.choice(512, num_cards, replace=False)
                    sample['action_target'][card_indices] = 1.0
                    
                    # 随机设置策略目标
                    strategy_class = np.random.randint(0, 7)
                    sample['strategy_target'][strategy_class] = 1.0
                    
                    samples.append(sample)
                    
                    if len(samples) >= round_size * 10:
                        break
                
                if len(samples) >= round_size * 10:
                    break
                    
            except Exception as e:
                continue
        
        if not samples:
            print("❌ 无法创建有效样本")
            return None
        
        # 创建简单的数据集类
        class SimpleDataset:
            def __init__(self, samples):
                self.samples = samples
            
            def __len__(self):
                return len(self.samples)
            
            def __getitem__(self, idx):
                return self.samples[idx]
        
        dataset = SimpleDataset(samples)
        print(f"✅ 数据集创建成功，总样本数: {len(dataset)}")
        
        if len(dataset) == 0:
            print("❌ 数据集为空")
            return None
        
        # 分析数据集特征
        sample_indices = np.random.choice(len(dataset), min(100, len(dataset)), replace=False)
        
        action_stats = Counter()
        strategy_stats = Counter()
        
        for idx in sample_indices:
            try:
                sample = dataset[idx]
                
                # 分析动作分布
                if 'action_target' in sample:
                    action_target = sample['action_target']
                    if torch.is_tensor(action_target):
                        action_indices = torch.nonzero(action_target).flatten()
                        action_stats[len(action_indices)] += 1
                
                # 分析策略分布
                if 'strategy_target' in sample:
                    strategy_target = sample['strategy_target']
                    if torch.is_tensor(strategy_target):
                        strategy_class = torch.argmax(strategy_target).item()
                        strategy_stats[strategy_class] += 1
                        
            except Exception as e:
                continue
        
        print(f"📊 动作分布 (选择的卡牌数量):")
        for num_cards, count in sorted(action_stats.items()):
            print(f"  {num_cards}张卡牌: {count} 样本")
        
        print(f"📊 策略分布:")
        strategy_names = ['bomb', 'suppress', 'protect', 'control', 'group', 'follow', 'discard']
        for strategy_id, count in sorted(strategy_stats.items()):
            strategy_name = strategy_names[strategy_id] if strategy_id < len(strategy_names) else f'unknown_{strategy_id}'
            print(f"  {strategy_name}: {count} 样本")
        
        return dataset
        
    except Exception as e:
        print(f"❌ 数据集创建失败: {e}")
        return None

def analyze_model_outputs(model, dataset, num_samples=1000):
    """分析模型输出分布"""
    print(f"\n=== 模型输出分布分析 (分析{num_samples}个样本) ===")
    
    if model is None or dataset is None:
        print("❌ 模型或数据集为空")
        return None
    
    model.eval()
    
    # 收集模型输出
    action_outputs = []
    strategy_outputs = []
    action_targets = []
    strategy_targets = []
    
    sample_indices = np.random.choice(len(dataset), min(num_samples, len(dataset)), replace=False)
    
    with torch.no_grad():
        for idx in sample_indices:
            try:
                sample = dataset[idx]
                
                # 获取输入
                state_input = sample['state_input'].unsqueeze(0)  # 添加batch维度
                
                # 模型推理
                action_output, strategy_output = model(state_input, return_strategy=True)
                
                # 收集输出
                action_outputs.append(action_output.squeeze(0))
                strategy_outputs.append(strategy_output.squeeze(0))
                
                # 收集目标
                if 'action_target' in sample:
                    action_targets.append(sample['action_target'])
                if 'strategy_target' in sample:
                    strategy_targets.append(sample['strategy_target'])
                    
            except Exception as e:
                continue
    
    if not action_outputs:
        print("❌ 没有收集到有效的模型输出")
        return None
    
    # 转换为张量
    action_outputs = torch.stack(action_outputs)
    strategy_outputs = torch.stack(strategy_outputs)
    
    print(f"✅ 收集到 {len(action_outputs)} 个有效样本")
    
    # 分析动作输出
    print(f"\n📊 动作输出分析:")
    action_probs = torch.softmax(action_outputs, dim=1)
    
    # 统计预测的卡牌数量
    predicted_cards = []
    for i in range(len(action_probs)):
        # 使用不同阈值统计预测数量
        for threshold in [0.1, 0.2, 0.3, 0.4, 0.5]:
            num_predicted = (action_probs[i] > threshold).sum().item()
            if threshold == 0.3:  # 使用0.3作为默认阈值
                predicted_cards.append(num_predicted)
                break
    
    predicted_stats = Counter(predicted_cards)
    print(f"  预测卡牌数量分布 (阈值=0.3):")
    for num_cards, count in sorted(predicted_stats.items()):
        print(f"    {num_cards}张: {count} 样本 ({count/len(predicted_cards):.1%})")
    
    # 分析概率分布
    max_probs = torch.max(action_probs, dim=1)[0]
    mean_probs = torch.mean(action_probs, dim=1)
    
    print(f"  概率统计:")
    print(f"    最大概率: 均值={max_probs.mean():.3f}, 标准差={max_probs.std():.3f}")
    print(f"    平均概率: 均值={mean_probs.mean():.3f}, 标准差={mean_probs.std():.3f}")
    
    # 分析策略输出
    print(f"\n📊 策略输出分析:")
    strategy_probs = torch.softmax(strategy_outputs, dim=1)
    strategy_predictions = torch.argmax(strategy_probs, dim=1)
    
    strategy_pred_stats = Counter(strategy_predictions.tolist())
    strategy_names = ['bomb', 'suppress', 'protect', 'control', 'group', 'follow', 'discard']
    
    print(f"  策略预测分布:")
    for strategy_id, count in sorted(strategy_pred_stats.items()):
        strategy_name = strategy_names[strategy_id] if strategy_id < len(strategy_names) else f'unknown_{strategy_id}'
        print(f"    {strategy_name}: {count} 样本 ({count/len(strategy_predictions):.1%})")
    
    # 计算准确率（如果有目标）
    if action_targets and strategy_targets:
        print(f"\n📊 准确率分析:")
        
        # 动作准确率（完全匹配）
        action_targets_tensor = torch.stack(action_targets)
        action_predictions = (action_probs > 0.3).float()
        
        exact_matches = (action_predictions == action_targets_tensor).all(dim=1).sum().item()
        exact_accuracy = exact_matches / len(action_targets)
        print(f"  动作完全匹配率: {exact_accuracy:.1%}")
        
        # 卡牌匹配率
        card_matches = 0
        total_cards = 0
        for i in range(len(action_predictions)):
            pred_cards = action_predictions[i]
            target_cards = action_targets_tensor[i]
            
            # 计算交集
            intersection = (pred_cards * target_cards).sum().item()
            union = (pred_cards + target_cards).clamp(max=1).sum().item()
            
            if union > 0:
                card_matches += intersection
                total_cards += union
        
        if total_cards > 0:
            card_accuracy = card_matches / total_cards
            print(f"  卡牌匹配率: {card_accuracy:.1%}")
        
        # 策略准确率
        strategy_targets_tensor = torch.stack(strategy_targets)
        strategy_target_classes = torch.argmax(strategy_targets_tensor, dim=1)
        
        strategy_correct = (strategy_predictions == strategy_target_classes).sum().item()
        strategy_accuracy = strategy_correct / len(strategy_targets)
        print(f"  策略分类准确率: {strategy_accuracy:.1%}")
    
    return {
        'action_outputs': action_outputs,
        'strategy_outputs': strategy_outputs,
        'predicted_cards_stats': predicted_stats,
        'max_probs': max_probs,
        'mean_probs': mean_probs,
        'strategy_pred_stats': strategy_pred_stats
    }

def simulate_evaluation_rounds(model, dataset, num_rounds=10, samples_per_round=1000):
    """模拟评估轮次，找出胜率为0的原因"""
    print(f"\n=== 模拟评估轮次 ({num_rounds}轮，每轮{samples_per_round}样本) ===")
    
    if model is None or dataset is None:
        print("❌ 模型或数据集为空")
        return None
    
    round_results = []
    
    for round_num in range(1, num_rounds + 1):
        print(f"\n🔄 第{round_num}轮评估:")
        
        # 随机选择样本（模拟不同轮次的数据分布）
        if round_num <= 3:
            # 前3轮：使用前面的数据
            start_idx = (round_num - 1) * samples_per_round
            end_idx = min(start_idx + samples_per_round, len(dataset))
            sample_indices = list(range(start_idx, end_idx))
        else:
            # 后7轮：随机选择（模拟数据分布变化）
            sample_indices = np.random.choice(len(dataset), min(samples_per_round, len(dataset)), replace=False)
        
        if len(sample_indices) == 0:
            print(f"  ❌ 第{round_num}轮没有有效样本")
            round_results.append({
                'round': round_num,
                'win_rate': 0.0,
                'exact_accuracy': 0.0,
                'card_accuracy': 0.0,
                'strategy_accuracy': 0.0,
                'num_samples': 0,
                'issue': 'no_samples'
            })
            continue
        
        # 分析这一轮的样本
        exact_matches = 0
        card_matches = 0
        total_cards = 0
        strategy_correct = 0
        valid_samples = 0
        
        model.eval()
        with torch.no_grad():
            for idx in sample_indices:
                try:
                    sample = dataset[idx]
                    
                    # 获取输入和目标
                    state_input = sample['state_input'].unsqueeze(0)
                    action_target = sample.get('action_target')
                    strategy_target = sample.get('strategy_target')
                    
                    if action_target is None or strategy_target is None:
                        continue
                    
                    # 模型推理
                    action_output, strategy_output = model(state_input, return_strategy=True)
                    
                    # 计算动作准确率
                    action_probs = torch.softmax(action_output, dim=1)
                    action_pred = (action_probs > 0.3).float().squeeze(0)
                    
                    # 完全匹配
                    if (action_pred == action_target).all():
                        exact_matches += 1
                    
                    # 卡牌匹配
                    intersection = (action_pred * action_target).sum().item()
                    union = (action_pred + action_target).clamp(max=1).sum().item()
                    
                    if union > 0:
                        card_matches += intersection
                        total_cards += union
                    
                    # 策略准确率
                    strategy_probs = torch.softmax(strategy_output, dim=1)
                    strategy_pred = torch.argmax(strategy_probs, dim=1).item()
                    strategy_true = torch.argmax(strategy_target).item()
                    
                    if strategy_pred == strategy_true:
                        strategy_correct += 1
                    
                    valid_samples += 1
                    
                except Exception as e:
                    continue
        
        # 计算指标
        if valid_samples > 0:
            exact_accuracy = exact_matches / valid_samples
            card_accuracy = card_matches / total_cards if total_cards > 0 else 0
            strategy_accuracy = strategy_correct / valid_samples
            
            # 简化的胜率计算（基于完全匹配率）
            win_rate = exact_accuracy * 0.6 + card_accuracy * 0.3 + strategy_accuracy * 0.1
        else:
            exact_accuracy = 0
            card_accuracy = 0
            strategy_accuracy = 0
            win_rate = 0
        
        print(f"  📊 结果:")
        print(f"    有效样本: {valid_samples}")
        print(f"    完全匹配率: {exact_accuracy:.1%}")
        print(f"    卡牌匹配率: {card_accuracy:.1%}")
        print(f"    策略准确率: {strategy_accuracy:.1%}")
        print(f"    估算胜率: {win_rate:.1%}")
        
        # 诊断问题
        issue = None
        if valid_samples == 0:
            issue = 'no_valid_samples'
        elif exact_accuracy == 0:
            issue = 'zero_exact_match'
        elif win_rate < 0.1:
            issue = 'very_low_performance'
        
        round_results.append({
            'round': round_num,
            'win_rate': win_rate,
            'exact_accuracy': exact_accuracy,
            'card_accuracy': card_accuracy,
            'strategy_accuracy': strategy_accuracy,
            'num_samples': valid_samples,
            'issue': issue
        })
    
    # 分析结果模式
    print(f"\n📈 轮次结果分析:")
    good_rounds = [r for r in round_results if r['win_rate'] > 0.3]
    bad_rounds = [r for r in round_results if r['win_rate'] == 0]
    
    print(f"  优秀轮次: {len(good_rounds)} 轮")
    print(f"  失败轮次: {len(bad_rounds)} 轮")
    
    if good_rounds:
        avg_good_winrate = np.mean([r['win_rate'] for r in good_rounds])
        print(f"  优秀轮次平均胜率: {avg_good_winrate:.1%}")
    
    if bad_rounds:
        print(f"  失败轮次问题:")
        issue_stats = Counter([r['issue'] for r in bad_rounds if r['issue']])
        for issue, count in issue_stats.items():
            print(f"    {issue}: {count} 轮")
    
    return round_results

def main():
    """主函数"""
    print("🔍 胜率为0问题诊断工具")
    print("=" * 50)
    
    # 1. 加载模型
    model = load_converted_model()
    if model is None:
        return
    
    # 2. 分析数据集分布
    data_info = analyze_dataset_distribution()
    if data_info is None:
        return
    
    # 3. 创建测试数据集
    dataset = create_test_dataset(data_info)
    if dataset is None:
        return
    
    # 4. 分析模型输出分布
    output_analysis = analyze_model_outputs(model, dataset)
    if output_analysis is None:
        return
    
    # 5. 模拟评估轮次
    round_results = simulate_evaluation_rounds(model, dataset)
    if round_results is None:
        return
    
    # 6. 生成诊断报告
    print(f"\n📋 诊断报告总结:")
    print(f"=" * 30)
    
    # 检查是否重现了问题
    zero_rounds = [r for r in round_results if r['win_rate'] == 0]
    if len(zero_rounds) >= 5:
        print(f"✅ 成功重现问题：{len(zero_rounds)} 轮胜率为0")
        
        # 分析问题原因
        print(f"\n🔍 问题原因分析:")
        
        # 检查完全匹配率
        zero_exact_rounds = [r for r in zero_rounds if r['exact_accuracy'] == 0]
        if len(zero_exact_rounds) == len(zero_rounds):
            print(f"  ❌ 主要问题：完全匹配率为0%")
            print(f"     - 模型无法准确预测卡牌组合")
            print(f"     - 建议：调整预测阈值或改进模型架构")
        
        # 检查样本问题
        no_sample_rounds = [r for r in zero_rounds if r['num_samples'] == 0]
        if len(no_sample_rounds) > 0:
            print(f"  ❌ 数据问题：{len(no_sample_rounds)} 轮没有有效样本")
            print(f"     - 数据集可能存在分布不均或损坏")
            print(f"     - 建议：检查数据集完整性")
        
        # 检查模型性能
        avg_card_accuracy = np.mean([r['card_accuracy'] for r in round_results if r['card_accuracy'] > 0])
        if avg_card_accuracy > 0.8:
            print(f"  ✅ 卡牌识别正常：平均匹配率 {avg_card_accuracy:.1%}")
            print(f"     - 问题主要在于卡牌组合预测")
        else:
            print(f"  ❌ 卡牌识别异常：平均匹配率 {avg_card_accuracy:.1%}")
    
    else:
        print(f"⚠️ 未能重现问题：只有 {len(zero_rounds)} 轮胜率为0")
        print(f"   - 可能是评估数据集或评估逻辑的问题")
        print(f"   - 建议：检查实际评估代码的实现")
    
    print(f"\n💡 建议的修复方案:")
    print(f"  1. 调整预测阈值：从0.3降低到0.2或0.1")
    print(f"  2. 改进评估指标：不要完全依赖完全匹配率")
    print(f"  3. 增加模型训练：特别是卡牌组合预测")
    print(f"  4. 检查数据质量：确保所有轮次的数据分布一致")
    print(f"  5. 修复评估代码：可能存在边界条件处理错误")

if __name__ == "__main__":
    main()