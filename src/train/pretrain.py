import sys
import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np

# **修复**：设置Windows控制台编码为UTF-8
if sys.platform == 'win32':
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except:
        pass

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.knowledge_processor.replay_parser import ReplayParser
from src.rl_agent.model import GuandanPolicyNet

class GuandanDataset(Dataset):
    def __init__(self, data):
        self.data = data
        
    def __len__(self):
        return len(self.data)
        
    def __getitem__(self, idx):
        state_dict, action_cards = self.data[idx]
        
        # **关键修复**：使用与推理代码相同的编码方式
        # 必须与 rl_decision_engine.py 中的 _card_to_index 保持一致！
        def card_to_index(card_code):
            """与 rl_decision_engine.py 中的编码方式完全一致"""
            suit_map = {'S': 0, 'H': 1, 'C': 2, 'D': 3}
            rank_map = {
                '2': 0, '3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6, '9': 7,
                'T': 8, 'J': 9, 'Q': 10, 'K': 11, 'A': 12,
                'B': 13,  # 小王
                'R': 14   # 大王
            }
            if len(card_code) >= 2:
                suit = card_code[0]
                rank = card_code[1]
                suit_val = suit_map.get(suit, 0)
                rank_val = rank_map.get(rank, 0)
                idx = suit_val * 15 + rank_val
                return min(idx, 59)  # 确保在0-59范围内
            return 0
        
        # Convert state_dict to vector (512维，增强版：包含策略特征)
        state_vec = np.zeros(512, dtype=np.float32)
        
        # 1. Encode Hand (0-59维) - 使用与推理代码相同的编码
        for card in state_dict['hand']:
            card_idx = card_to_index(card)
            if card_idx < 60:
                state_vec[card_idx] = 1.0
        
        # 2. 编码游戏阶段（120-122维）
        # 从历史数据中可能没有游戏阶段信息，使用默认值（中期）
        game_phase = state_dict.get('game_phase', 1)  # 0=开局, 1=中期, 2=残局
        if game_phase < 3:
            state_vec[120 + game_phase] = 1.0
        else:
            state_vec[121] = 1.0  # 默认中期
        
        # 3. 编码玩家剩余牌数（123-126维）
        # 从历史数据中可能没有这些信息，使用默认值
        player_rest_cards = state_dict.get('player_rest_cards', [27, 27, 27, 27])
        for i, card_count in enumerate(player_rest_cards[:4]):
            state_vec[123 + i] = card_count / 27.0  # 归一化
        
        # 4. 编码上一步动作（127-151维）
        last_action = state_dict.get('last_action', {})
        if last_action:
            action_type = last_action.get('type', '')
            action_cards = last_action.get('cards', [])
            
            # 动作类型编码（127-136维）
            action_type_map = {
                'PASS': 0, 'Single': 1, 'Pair': 2, 'Trips': 3,
                'Straight': 4, 'ThreeWithTwo': 5, 'Bomb': 6,
                'StraightFlush': 7, 'ThreePair': 8, 'TwoTrips': 9
            }
            action_type_idx = action_type_map.get(action_type, 0)
            if action_type_idx < 10:
                state_vec[127 + action_type_idx] = 1.0
            
            # 动作牌点编码（137-151维）
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
        # 从历史数据中可能没有这些信息，使用默认值
        state_vec[152] = state_dict.get('can_follow', 0.0)  # 是否能顺牌
        state_vec[153] = state_dict.get('can_followup', 0.0)  # 是否能跟牌
        state_vec[154] = state_dict.get('need_control', 0.0)  # 是否需要控牌
            
        # Convert action_cards to vector (Target)
        # 注意：动作空间是512维（与状态空间一致），不是108维
        action_vec = np.zeros(512, dtype=np.float32)
        for card in action_cards:
            card_idx = card_to_index(card)
            if card_idx < 512:
                action_vec[card_idx] = 1.0
            
        return torch.FloatTensor(state_vec), torch.FloatTensor(action_vec)

def train_bc(data_dir="game_records", epochs=30, batch_size=64, lr=0.0005, model_path="models/bc_model_v1.pth", dropout_rate=0.1):
    """
    行为克隆预训练
    
    Args:
        data_dir: 训练数据目录
        epochs: 训练轮数
        batch_size: 批次大小
        lr: 学习率
        model_path: 模型保存路径
    """
    print("Starting Behavior Cloning Pre-training...")
    print(f"Data directory: {data_dir}")
    print(f"Epochs: {epochs}, Batch size: {batch_size}, Learning rate: {lr}")
    
    # 1. Load Data
    parser = ReplayParser(data_dir)
    replays = parser.load_replays()
    raw_data = parser.extract_training_data(replays)
    print(f"Loaded {len(raw_data)} samples.")
    
    if len(raw_data) == 0:
        print("No data found. Exiting.")
        return

    dataset = GuandanDataset(raw_data)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    
    # 2. Setup Model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    # **关键修复**：模型输入输出维度必须与推理代码一致
    # 输入：512维状态向量
    # 输出：512维动作向量（每个维度表示是否选择对应的卡牌索引）
    # **优化**: 使用降低的dropout_rate (0.1)，减少过拟合，提高输出概率
    model = GuandanPolicyNet(input_dim=512, hidden_dim=256, output_dim=512, dropout_rate=dropout_rate).to(device)
    print(f"Model: input_dim=512, output_dim=512, dropout_rate={dropout_rate} (matching inference code)")
    optimizer = optim.Adam(model.parameters(), lr=lr)
    
    # **优化**: 使用加权损失函数，增加对预测过少的惩罚
    # 权重策略：对于正样本（应该选择的卡牌），给予更高权重（2.0倍）
    # 这样可以鼓励模型更积极地预测卡牌，减少预测过少的问题
    # 使用pos_weight=2.0，意味着正样本的损失权重是负样本的2倍
    pos_weight = torch.tensor(2.0).to(device)  # 正样本权重：2.0（增加对预测过少的惩罚）
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)  # 加权BCE损失
    
    # **优化**：添加学习率衰减
    # 每10轮衰减50%，帮助模型更稳定地收敛
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.5)
    
    # 3. Training Loop
    for epoch in range(epochs):
        total_loss = 0
        for states, actions in dataloader:
            states, actions = states.to(device), actions.to(device)
            
            optimizer.zero_grad()
            logits = model(states)
            # **优化**: 使用加权损失函数，增加对预测过少的惩罚
            loss = criterion(logits, actions)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            
        avg_loss = total_loss / len(dataloader)
        current_lr = optimizer.param_groups[0]['lr']
        print(f"Epoch {epoch+1}/{epochs}, Loss: {avg_loss:.4f}, LR: {current_lr:.6f}")
        
        # 更新学习率
        scheduler.step()
        
    # 4. Save Model
    model_dir = os.path.dirname(model_path)
    if model_dir:
        os.makedirs(model_dir, exist_ok=True)
    torch.save(model.state_dict(), model_path)
    print(f"Model saved to {model_path}")

if __name__ == "__main__":
    train_bc()
