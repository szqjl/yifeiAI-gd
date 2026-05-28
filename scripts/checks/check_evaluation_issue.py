"""检查评估失败和训练数据问题"""
import json
from pathlib import Path
import torch

print("="*60)
print("1. 检查评估器问题")
print("="*60)

# 检查游戏记录文件匹配
game_records_dir = Path("game_records")
all_files = list(game_records_dir.glob("*.json"))
yf1_files = list(game_records_dir.glob("*yf1_m1*.json"))
client_pattern = list(game_records_dir.glob("*yf1_m1*client*.json"))
opponent_pattern = list(game_records_dir.glob("*yf1_m1*opponent*.json"))

print(f"总游戏记录文件: {len(all_files)}")
print(f"yf1_m1文件: {len(yf1_files)}")
print(f"匹配 *yf1_m1*client*: {len(client_pattern)}")
print(f"匹配 *yf1_m1*opponent*: {len(opponent_pattern)}")

if yf1_files:
    sample_file = yf1_files[0]
    print(f"\n示例文件名: {sample_file.name}")
    with open(sample_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"文件内容类型: {type(data)}")
    if isinstance(data, dict):
        print(f"记录键: {list(data.keys())[:10]}")
        if 'game_info' in data:
            print(f"game_info: {data['game_info']}")
        if 'result' in data:
            print(f"result键: {list(data['result'].keys()) if isinstance(data['result'], dict) else type(data['result'])}")

print("\n" + "="*60)
print("2. 检查训练数据问题")
print("="*60)

# 检查训练数据加载
try:
    import sys
    sys.path.insert(0, 'src/train')
    from simple_data_loader import create_simple_dataloader
    
    dataloader = create_simple_dataloader(
        data_dir="game_records",
        batch_size=4,
        max_samples=100,
        shuffle=False
    )
    
    if len(dataloader.dataset) > 0:
        print(f"数据集大小: {len(dataloader.dataset)}")
        # 检查第一个batch
        for batch_idx, batch in enumerate(dataloader):
            if batch_idx == 0:
                state_vec, action_vec, strategy_type = batch
                print(f"Batch形状:")
                print(f"  state_vec: {state_vec.shape}")
                print(f"  action_vec: {action_vec.shape}")
                print(f"  strategy_type: {strategy_type.shape}")
                print(f"\nAction向量统计:")
                print(f"  总和: {action_vec.sum().item()}")
                print(f"  非零元素: {(action_vec > 0).sum().item()}")
                print(f"  每样本平均: {action_vec.sum(dim=1).float().mean().item()}")
                break
    else:
        print("❌ 数据集为空！")
except Exception as e:
    print(f"❌ 数据加载失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("3. 检查模型")
print("="*60)

model_path = Path("models/bc_model_stage7_optimized.pth")
if model_path.exists():
    print(f"✅ 模型文件存在: {model_path.stat().st_size / 1024 / 1024:.2f} MB")
    try:
        checkpoint = torch.load(model_path, map_location='cpu')
        print(f"✅ 模型可以加载")
        print(f"模型键: {list(checkpoint.keys())}")
        if 'model_state_dict' in checkpoint:
            print(f"✅ 包含model_state_dict")
        if 'training_history' in checkpoint:
            history = checkpoint['training_history']
            if history:
                last_epoch = history[-1]
                print(f"最后epoch信息:")
                print(f"  avg_true_cards: {last_epoch.get('avg_true_cards', 'N/A')}")
                print(f"  avg_predicted_cards: {last_epoch.get('avg_predicted_cards', 'N/A')}")
    except Exception as e:
        print(f"❌ 模型加载失败: {e}")
else:
    print("❌ 模型文件不存在")

print("\n" + "="*60)
print("检查完成")
print("="*60)
