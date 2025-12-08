import sys
import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np

# **修复**：设置Windows控制台编码为UTF-8
try:
    from src.utils.encoding_fix import fix_windows_console_encoding
    fix_windows_console_encoding()
except ImportError:
    # 如果导入失败，使用备用方案
    if sys.platform == 'win32':
        try:
            import io
            if hasattr(sys.stdout, 'buffer'):
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            if hasattr(sys.stderr, 'buffer'):
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
        """
        获取训练样本
        
        数据格式：
        - state_dict: 状态字典，包含：
          - hand: 手牌列表
          - history: 历史动作
          - current_player: 当前玩家
          - hands: 所有玩家的手牌
          - last_action: 上一步动作
          - action_type: 当前动作类型
          - game_phase: 游戏阶段
          - cur_rank: 当前级牌
          - player_rest_cards: 玩家剩余牌数
          - strategy_type: 策略类型（新增）
          - strategy_reason: 策略原因（新增）
          - strategy_effectiveness: 策略效果（新增）
        - action_cards: 动作卡牌列表
        """
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
        
        # 6. 编码策略类型（155-162维）- 新增：支持策略信息
        # 策略类型：bomb, suppress, protect, control, group, follow, discard, unknown
        strategy_type = state_dict.get('strategy_type', 'unknown')
        strategy_type_map = {
            'bomb': 0, 'suppress': 1, 'protect': 2, 'control': 3,
            'group': 4, 'follow': 5, 'discard': 6, 'unknown': 7
        }
        strategy_type_idx = strategy_type_map.get(strategy_type, 7)
        if strategy_type_idx < 8 and (155 + strategy_type_idx) < 512:
            state_vec[155 + strategy_type_idx] = 1.0
        
        # 7. 编码策略效果（163维）- 新增：支持策略效果信息
        # 策略效果分数归一化（假设最大值为30，归一化到0-1）
        strategy_effectiveness = state_dict.get('strategy_effectiveness', 0.0)
        if 163 < 512:
            state_vec[163] = min(strategy_effectiveness / 30.0, 1.0)  # 归一化到[0, 1]
            
        # Convert action_cards to vector (Target)
        # 注意：动作空间是512维（与状态空间一致），不是108维
        action_vec = np.zeros(512, dtype=np.float32)
        for card in action_cards:
            card_idx = card_to_index(card)
            if card_idx < 512:
                action_vec[card_idx] = 1.0
            
        # 8. 提取策略标签（用于多任务学习）- 阶段2任务2新增
        # 策略类型：bomb, suppress, protect, control, group, follow, discard, unknown
        strategy_type = state_dict.get('strategy_type', 'unknown')
        strategy_type_map = {
            'bomb': 0, 'suppress': 1, 'protect': 2, 'control': 3,
            'group': 4, 'follow': 5, 'discard': 6, 'unknown': 7
        }
        strategy_type_idx = strategy_type_map.get(strategy_type, 7)
        # 返回策略类型索引（0-7），7表示unknown，在损失计算中会被忽略
        
        return torch.FloatTensor(state_vec), torch.FloatTensor(action_vec), strategy_type_idx

def train_bc(data_dir="game_records", epochs=30, batch_size=64, lr=0.0003, model_path="models/bc_model_v1.pth", 
             dropout_rate=0.1, enable_strategy_head=True, action_loss_weight=1.5, strategy_loss_weight=0.3):
    """
    行为克隆预训练（支持多任务学习）
    
    **最优配置（基于历次训练效果汇总.md）**:
    - epochs: 30-50（根据数据量选择，大数据量用50）
    - batch_size: 64（最优批次大小）
    - lr: 0.0003（稳定学习率，配合学习率衰减）
    - dropout_rate: 0.1（平衡过拟合和输出概率）
    - 学习率衰减: StepLR(step_size=10, gamma=0.5)（每10轮衰减50%）
    - 损失函数: 加权BCE(pos_weight=2.0)（惩罚预测过少）
    
    **阶段2新增（多任务学习）**:
    - enable_strategy_head: 是否启用策略分类头（默认True）
    - action_loss_weight: 动作预测损失权重（阶段3调整为1.5，原1.0）
    - strategy_loss_weight: 策略分类损失权重（阶段3调整为0.3，原0.5）
    
    Args:
        data_dir: 训练数据目录
        epochs: 训练轮数（推荐30-50）
        batch_size: 批次大小（推荐64）
        lr: 学习率（推荐0.0003）
        model_path: 模型保存路径
        dropout_rate: Dropout比率（推荐0.1）
        enable_strategy_head: 是否启用策略分类头（阶段2新增）
        action_loss_weight: 动作预测损失权重α（阶段2新增）
        strategy_loss_weight: 策略分类损失权重β（阶段2新增）
    """
    print("Starting Behavior Cloning Pre-training...")
    print(f"Data directory: {data_dir}")
    print(f"Epochs: {epochs}, Batch size: {batch_size}, Learning rate: {lr}")
    print(f"[最优配置] 学习率衰减: StepLR(step_size=10, gamma=0.5), 损失函数: 加权BCE(pos_weight=2.0)")
    if enable_strategy_head:
        print(f"[阶段2多任务学习] 策略分类头: 启用, 损失权重: α={action_loss_weight}, β={strategy_loss_weight}")
    else:
        print(f"[阶段2多任务学习] 策略分类头: 禁用（单任务学习）")
    
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
    # **阶段2新增**: 启用策略分类头（多任务学习）
    model = GuandanPolicyNet(
        input_dim=512, 
        hidden_dim=256, 
        output_dim=512, 
        dropout_rate=dropout_rate,
        strategy_num_classes=7,
        enable_strategy_head=enable_strategy_head
    ).to(device)
    print(f"Model: input_dim=512, output_dim=512, dropout_rate={dropout_rate}, strategy_head={enable_strategy_head} (matching inference code)")
    optimizer = optim.Adam(model.parameters(), lr=lr)
    
    # **优化**: 使用加权损失函数，增加对预测过少的惩罚
    # 权重策略：对于正样本（应该选择的卡牌），给予更高权重（2.0倍）
    # 这样可以鼓励模型更积极地预测卡牌，减少预测过少的问题
    # 使用pos_weight=2.0，意味着正样本的损失权重是负样本的2倍
    pos_weight = torch.tensor(2.0).to(device)  # 正样本权重：2.0（增加对预测过少的惩罚）
    action_criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)  # 动作预测损失（加权BCE）
    
    # **阶段2新增**: 策略分类损失（交叉熵损失）
    # 注意：CrossEntropyLoss内部会应用Softmax，所以不需要在模型输出上应用Softmax
    strategy_criterion = nn.CrossEntropyLoss(ignore_index=7) if enable_strategy_head else None  # 忽略unknown类别（索引7）
    
    # **优化**：添加学习率衰减
    # 每10轮衰减50%，帮助模型更稳定地收敛
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.5)
    
    # 3. Training Loop
    # **阶段2任务3新增**: 评估指标记录
    training_history = {
        'epochs': [],
        'total_loss': [],
        'action_loss': [],
        'strategy_loss': [],
        'action_exact_accuracy': [],
        'action_card_accuracy': [],
        'strategy_accuracy': [],
        'strategy_accuracy_by_class': {i: [] for i in range(7)},  # 7个策略类别
        'strategy_understanding_rate': []  # 策略理解率（动作预测和策略分类都正确）
    }
    
    for epoch in range(epochs):
        total_loss = 0
        total_action_loss = 0
        total_strategy_loss = 0
        strategy_loss_count = 0  # 统计有效策略损失样本数
        
        # **阶段2任务3新增**: 评估指标统计
        total_samples = 0
        correct_action_predictions = 0  # 完全匹配的动作预测数
        total_action_cards = 0
        matched_action_cards = 0  # 匹配的卡牌数
        
        total_strategy_samples = 0  # 有效策略样本数（排除unknown）
        correct_strategy_predictions = 0  # 正确的策略分类数
        strategy_correct_by_class = {i: {'correct': 0, 'total': 0} for i in range(7)}  # 各类别统计
        
        strategy_understanding_count = 0  # 策略理解正确数（动作和策略都正确）
        
        model.train()  # 确保模型处于训练模式
        
        for batch in dataloader:
            # 处理数据：支持多任务学习（返回策略标签）
            if enable_strategy_head and len(batch) == 3:
                states, actions, strategy_labels = batch
                strategy_labels = strategy_labels.to(device)
            else:
                # 向后兼容：如果数据集不返回策略标签，只使用动作预测
                states, actions = batch[0], batch[1]
                strategy_labels = None
            
            states, actions = states.to(device), actions.to(device)
            
            optimizer.zero_grad()
            
            # 前向传播
            if enable_strategy_head and strategy_labels is not None:
                # 多任务学习：同时返回动作预测和策略分类
                action_logits, strategy_logits = model(states, return_strategy=True)
                
                # 计算动作预测损失
                action_loss = action_criterion(action_logits, actions)
                
                # 计算策略分类损失（忽略unknown类别，即索引7）
                # 只计算非unknown样本的损失
                valid_mask = (strategy_labels < 7)  # 排除unknown（索引7）
                if valid_mask.sum() > 0:
                    valid_strategy_labels = strategy_labels[valid_mask]
                    valid_strategy_logits = strategy_logits[valid_mask]
                    strategy_loss = strategy_criterion(valid_strategy_logits, valid_strategy_labels)
                    strategy_loss_count += valid_mask.sum().item()
                else:
                    strategy_loss = torch.tensor(0.0, device=device)
                
                # 组合损失
                total_batch_loss = action_loss_weight * action_loss + strategy_loss_weight * strategy_loss
                
                total_action_loss += action_loss.item()
                total_strategy_loss += strategy_loss.item()
            else:
                # 单任务学习：只使用动作预测
                action_logits = model(states, return_strategy=False)
                action_loss = action_criterion(action_logits, actions)
                total_batch_loss = action_loss
                total_action_loss += action_loss.item()
            
            # 反向传播
            total_batch_loss.backward()
            optimizer.step()
            
            total_loss += total_batch_loss.item()
            
            # **阶段2任务3新增**: 计算评估指标（在训练模式下，使用阈值预测）
            with torch.no_grad():
                # 动作预测准确率
                # **基线评估参数**：使用阶段0验证的标准参数作为统一标尺
                # 所有阶段的模型评估必须使用此基线参数，不能为了提升准确率而调整
                action_probs = torch.sigmoid(action_logits)
                action_probs = action_probs * 5.0  # 基线缩放因子（阶段0基线参数）
                action_probs = torch.clamp(action_probs, 0, 1)
                action_predictions = (action_probs > 0.3).float()  # 基线阈值（阶段0基线参数）
                
                # 确保action_predictions和actions维度一致
                if action_predictions.shape != actions.shape:
                    min_dim = min(action_predictions.shape[1], actions.shape[1])
                    action_predictions = action_predictions[:, :min_dim]
                    actions = actions[:, :min_dim]
                
                # 完全匹配准确率
                exact_match = (action_predictions == actions).all(dim=1)
                batch_correct = exact_match.sum().item()
                correct_action_predictions += batch_correct
                total_samples += len(states)
                
                # 卡牌级别准确率
                batch_matched_cards = (action_predictions == actions).sum().item()
                batch_total_cards = actions.numel()
                matched_action_cards += batch_matched_cards
                total_action_cards += batch_total_cards
                
                # 策略分类准确率（如果启用策略分类头）
                if enable_strategy_head and strategy_labels is not None:
                    strategy_preds = torch.argmax(strategy_logits, dim=1)
                    valid_mask = (strategy_labels < 7)  # 排除unknown
                    
                    if valid_mask.sum() > 0:
                        valid_strategy_labels = strategy_labels[valid_mask]
                        valid_strategy_preds = strategy_preds[valid_mask]
                        
                        # 整体策略分类准确率
                        strategy_correct = (valid_strategy_preds == valid_strategy_labels)
                        correct_strategy_predictions += strategy_correct.sum().item()
                        total_strategy_samples += valid_mask.sum().item()
                        
                        # 各类别策略分类准确率
                        for label_idx in range(7):
                            class_mask = (valid_strategy_labels == label_idx)
                            if class_mask.sum() > 0:
                                strategy_correct_by_class[label_idx]['total'] += class_mask.sum().item()
                                class_correct = (valid_strategy_preds[class_mask] == valid_strategy_labels[class_mask])
                                strategy_correct_by_class[label_idx]['correct'] += class_correct.sum().item()
                        
                        # 策略理解率（动作预测和策略分类都正确）
                        if total_samples > 0:
                            # 对于有效策略样本，检查动作和策略是否都正确
                            # exact_match是(batch_size,)形状，valid_mask也是(batch_size,)形状
                            # 需要确保维度匹配
                            if exact_match.dim() == 1 and valid_mask.dim() == 1:
                                valid_exact_match = exact_match[valid_mask]
                                valid_strategy_correct = strategy_correct
                                # 确保两个tensor都是1维且长度相同
                                if valid_exact_match.shape == valid_strategy_correct.shape:
                                    both_correct = (valid_exact_match & valid_strategy_correct)
                                    strategy_understanding_count += both_correct.sum().item()
            
        avg_loss = total_loss / len(dataloader)
        avg_action_loss = total_action_loss / len(dataloader)
        avg_strategy_loss = total_strategy_loss / strategy_loss_count if strategy_loss_count > 0 else 0.0
        current_lr = optimizer.param_groups[0]['lr']
        
        # **阶段2任务3新增**: 计算评估指标
        action_exact_accuracy = correct_action_predictions / total_samples if total_samples > 0 else 0.0
        action_card_accuracy = matched_action_cards / total_action_cards if total_action_cards > 0 else 0.0
        strategy_accuracy = correct_strategy_predictions / total_strategy_samples if total_strategy_samples > 0 else 0.0
        strategy_understanding_rate = strategy_understanding_count / total_strategy_samples if total_strategy_samples > 0 else 0.0
        
        # 记录训练历史
        training_history['epochs'].append(epoch + 1)
        training_history['total_loss'].append(avg_loss)
        training_history['action_loss'].append(avg_action_loss)
        training_history['strategy_loss'].append(avg_strategy_loss)
        training_history['action_exact_accuracy'].append(action_exact_accuracy)
        training_history['action_card_accuracy'].append(action_card_accuracy)
        training_history['strategy_accuracy'].append(strategy_accuracy)
        training_history['strategy_understanding_rate'].append(strategy_understanding_rate)
        
        for label_idx in range(7):
            if strategy_correct_by_class[label_idx]['total'] > 0:
                class_accuracy = strategy_correct_by_class[label_idx]['correct'] / strategy_correct_by_class[label_idx]['total']
                training_history['strategy_accuracy_by_class'][label_idx].append(class_accuracy)
            else:
                training_history['strategy_accuracy_by_class'][label_idx].append(0.0)
        
        # **阶段2任务3新增**: 详细日志输出
        if enable_strategy_head and strategy_loss_count > 0:
            print(f"Epoch {epoch+1}/{epochs}:")
            print(f"  Loss - Total: {avg_loss:.4f}, Action: {avg_action_loss:.4f}, Strategy: {avg_strategy_loss:.4f}, LR: {current_lr:.6f}")
            print(f"  Action Accuracy - Exact: {action_exact_accuracy:.2%}, Card: {action_card_accuracy:.2%}")
            print(f"  Strategy Accuracy - Overall: {strategy_accuracy:.2%}, Understanding Rate: {strategy_understanding_rate:.2%}")
            
            # 各类别策略准确率（只显示有样本的类别）
            strategy_type_names = ['bomb', 'suppress', 'protect', 'control', 'group', 'follow', 'discard']
            class_accuracies = []
            for label_idx in range(7):
                if strategy_correct_by_class[label_idx]['total'] > 0:
                    class_acc = strategy_correct_by_class[label_idx]['correct'] / strategy_correct_by_class[label_idx]['total']
                    class_accuracies.append(f"{strategy_type_names[label_idx]}: {class_acc:.2%}")
            if class_accuracies:
                print(f"  Strategy Accuracy by Class - {', '.join(class_accuracies)}")
        else:
            print(f"Epoch {epoch+1}/{epochs}, Loss: {avg_loss:.4f}, Action Exact Accuracy: {action_exact_accuracy:.2%}, Action Card Accuracy: {action_card_accuracy:.2%}, LR: {current_lr:.6f}")
        
        # **阶段2任务3新增**: 保存模型检查点（每10个epoch保存一次）
        if (epoch + 1) % 10 == 0 or epoch == epochs - 1:
            checkpoint_path = model_path.replace('.pth', f'_epoch_{epoch+1}.pth')
            checkpoint_dir = os.path.dirname(checkpoint_path)
            if checkpoint_dir:
                os.makedirs(checkpoint_dir, exist_ok=True)
            torch.save({
                'epoch': epoch + 1,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'scheduler_state_dict': scheduler.state_dict(),
                'training_history': training_history,
                'loss': avg_loss,
                'action_exact_accuracy': action_exact_accuracy,
                'strategy_accuracy': strategy_accuracy,
            }, checkpoint_path)
            print(f"  [Checkpoint] Model saved to {checkpoint_path}")
        
        # 更新学习率
        scheduler.step()
        
    # 4. Save Model
    model_dir = os.path.dirname(model_path)
    if model_dir:
        os.makedirs(model_dir, exist_ok=True)
    
    # **阶段2任务3新增**: 保存最终模型和训练历史
    final_model_data = {
        'model_state_dict': model.state_dict(),
        'training_history': training_history,
        'final_epoch': epochs,
        'final_loss': training_history['total_loss'][-1] if training_history['total_loss'] else 0.0,
        'final_action_exact_accuracy': training_history['action_exact_accuracy'][-1] if training_history['action_exact_accuracy'] else 0.0,
        'final_strategy_accuracy': training_history['strategy_accuracy'][-1] if training_history['strategy_accuracy'] else 0.0,
        'final_strategy_understanding_rate': training_history['strategy_understanding_rate'][-1] if training_history['strategy_understanding_rate'] else 0.0,
    }
    torch.save(final_model_data, model_path)
    print(f"Model saved to {model_path}")
    
    # **阶段2任务3新增**: 保存训练历史到JSON文件
    import json
    history_file = model_path.replace('.pth', '_training_history.json')
    try:
        # 转换numpy类型为Python原生类型
        history_for_json = {
            'epochs': training_history['epochs'],
            'total_loss': [float(x) for x in training_history['total_loss']],
            'action_loss': [float(x) for x in training_history['action_loss']],
            'strategy_loss': [float(x) for x in training_history['strategy_loss']],
            'action_exact_accuracy': [float(x) for x in training_history['action_exact_accuracy']],
            'action_card_accuracy': [float(x) for x in training_history['action_card_accuracy']],
            'strategy_accuracy': [float(x) for x in training_history['strategy_accuracy']],
            'strategy_understanding_rate': [float(x) for x in training_history['strategy_understanding_rate']],
            'strategy_accuracy_by_class': {
                str(k): [float(x) for x in v] for k, v in training_history['strategy_accuracy_by_class'].items()
            }
        }
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history_for_json, f, indent=2, ensure_ascii=False)
        print(f"Training history saved to {history_file}")
    except Exception as e:
        print(f"[WARNING] Failed to save training history: {e}")
    
    # **阶段2任务3新增**: 输出最终训练结果摘要
    print("\n" + "="*60)
    print("训练完成摘要")
    print("="*60)
    if training_history['action_exact_accuracy']:
        print(f"最终动作预测准确率 - 完全匹配: {training_history['action_exact_accuracy'][-1]:.2%}, 卡牌级别: {training_history['action_card_accuracy'][-1]:.2%}")
    if training_history['strategy_accuracy']:
        print(f"最终策略分类准确率: {training_history['strategy_accuracy'][-1]:.2%}")
        print(f"最终策略理解率: {training_history['strategy_understanding_rate'][-1]:.2%}")
    print("="*60)

if __name__ == "__main__":
    train_bc()
