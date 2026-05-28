"""诊断训练问题"""
import sys
sys.path.insert(0, 'src/knowledge_processor')
sys.path.insert(0, 'src/train')

from replay_parser import ReplayParser
from pathlib import Path
import json
import torch

print("="*60)
print("训练问题诊断")
print("="*60)

# 1. 检查训练数据质量
print("\n1. 检查训练数据质量")
print("-"*60)

parser = ReplayParser('game_records')
replays = parser.load_replays()[:5]
print(f"加载了 {len(replays)} 个replay")

if replays:
    data = parser.extract_training_data(replays)
    print(f"提取了 {len(data)} 个训练样本")
    
    if data:
        # 统计action_cards分布
        empty_count = 0
        non_empty_count = 0
        card_counts = []
        
        for state_dict, action_cards in data[:100]:
            if isinstance(action_cards, list):
                if len(action_cards) == 0:
                    empty_count += 1
                else:
                    non_empty_count += 1
                    card_counts.append(len(action_cards))
        
        print(f"\n前100个样本统计:")
        print(f"  空action_cards: {empty_count}")
        print(f"  非空action_cards: {non_empty_count}")
        if card_counts:
            print(f"  平均卡牌数: {sum(card_counts)/len(card_counts):.2f}")
            print(f"  最大卡牌数: {max(card_counts)}")
            print(f"  最小卡牌数: {min(card_counts)}")
        
        # 检查一个样本的详细信息
        sample_state, sample_action = data[0]
        print(f"\n第一个样本详情:")
        print(f"  action_cards: {sample_action[:10] if len(sample_action) > 10 else sample_action}")
        print(f"  action_cards长度: {len(sample_action)}")
        print(f"  状态键: {list(sample_state.keys())[:5]}")

# 2. 检查数据加载器
print("\n2. 检查数据加载器")
print("-"*60)

try:
    from simple_data_loader import create_simple_dataloader
    
    dataloader = create_simple_dataloader(
        data_dir="game_records",
        batch_size=4,
        max_samples=100,
        shuffle=False
    )
    
    print(f"数据集大小: {len(dataloader.dataset)}")
    
    if len(dataloader.dataset) > 0:
        # 检查第一个batch
        for batch_idx, batch in enumerate(dataloader):
            if batch_idx == 0:
                state_vec, action_vec, strategy_type = batch
                print(f"\n第一个batch:")
                print(f"  state_vec形状: {state_vec.shape}")
                print(f"  action_vec形状: {action_vec.shape}")
                print(f"  strategy_type形状: {strategy_type.shape}")
                print(f"\n  action_vec统计:")
                print(f"    总和: {action_vec.sum().item()}")
                print(f"    非零元素: {(action_vec > 0).sum().item()}")
                print(f"    每样本平均: {action_vec.sum(dim=1).float().mean().item()}")
                print(f"    每样本最大: {action_vec.sum(dim=1).float().max().item()}")
                print(f"    每样本最小: {action_vec.sum(dim=1).float().min().item()}")
                
                # 检查是否有全0的样本
                zero_samples = (action_vec.sum(dim=1) == 0).sum().item()
                print(f"    全0样本数: {zero_samples}/{action_vec.size(0)}")
                break
    else:
        print("❌ 数据集为空！")
except Exception as e:
    print(f"❌ 数据加载失败: {e}")
    import traceback
    traceback.print_exc()

# 3. 检查模型参数
print("\n3. 检查模型和损失函数参数")
print("-"*60)

try:
    from stage7_optimized_training import EnhancedFocalLoss
    from models.optimized_guandan_net import OptimizedGuandanNet
    
    # 检查损失函数参数
    loss_fn = EnhancedFocalLoss(
        alpha=0.02,
        gamma=5.0,
        over_prediction_penalty=10.0,
        sparsity_reward=6650.513460159302
    )
    print(f"损失函数参数:")
    print(f"  alpha: {loss_fn.alpha}")
    print(f"  gamma: {loss_fn.gamma}")
    print(f"  over_prediction_penalty: {loss_fn.over_prediction_penalty}")
    print(f"  sparsity_reward: {loss_fn.sparsity_reward}")
    
    # 检查模型
    model = OptimizedGuandanNet()
    total_params = sum(p.numel() for p in model.parameters())
    print(f"\n模型参数:")
    print(f"  总参数数: {total_params:,}")
    
except Exception as e:
    print(f"❌ 检查模型失败: {e}")
    import traceback
    traceback.print_exc()

# 4. 检查训练历史
print("\n4. 检查训练历史")
print("-"*60)

training_history_file = Path("models/bc_model_stage7_optimized_training_history.json")
if training_history_file.exists():
    with open(training_history_file, 'r', encoding='utf-8') as f:
        history = json.load(f)
    
    if history:
        latest = history[-1]
        print(f"最新epoch: {latest.get('epoch')}")
        print(f"  损失: {latest.get('total_loss', 0):.2f}")
        print(f"  预测卡牌数: {latest.get('avg_predicted_cards', 0):.2f}")
        print(f"  真实卡牌数: {latest.get('avg_true_cards', 0):.2f}")
        print(f"  预测比例: {latest.get('prediction_ratio', 0):.2f}")
        
        # 检查趋势
        if len(history) > 1:
            first = history[0]
            print(f"\n训练趋势:")
            print(f"  损失变化: {first.get('total_loss', 0):.2f} -> {latest.get('total_loss', 0):.2f}")
            print(f"  预测比例变化: {first.get('prediction_ratio', 0):.2f} -> {latest.get('prediction_ratio', 0):.2f}")
            print(f"  真实卡牌数变化: {first.get('avg_true_cards', 0):.2f} -> {latest.get('avg_true_cards', 0):.2f}")

print("\n" + "="*60)
print("诊断完成")
print("="*60)
