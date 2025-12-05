import torch
import torch.nn as nn
import torch.nn.functional as F

class GuandanPolicyNet(nn.Module):
    def __init__(self, input_dim=512, hidden_dim=256, output_dim=512, dropout_rate=0.2):
        """
        Policy Network for Guandan AI
        
        Args:
            input_dim: 状态空间维度（512维，对应512个卡牌索引位置）
            hidden_dim: 隐藏层维度
            output_dim: 动作空间维度（512维，与状态空间一致，每个维度表示是否选择对应的卡牌）
            dropout_rate: Dropout比率（用于正则化，防止过拟合）
        """
        super(GuandanPolicyNet, self).__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, output_dim)
        # **优化**：添加Dropout层进行正则化
        self.dropout = nn.Dropout(dropout_rate)
        
    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = self.dropout(x)  # **优化**：添加Dropout
        x = F.relu(self.fc2(x))
        x = self.dropout(x)  # **优化**：添加Dropout
        logits = self.fc3(x)
        # Output logits for MultiBinary action selection
        # We will use BCEWithLogitsLoss for training if treating as multi-label classification
        # Or we can use it to sample actions
        return logits

    def get_action(self, state, deterministic=False, threshold=0.3):
        """
        Select action given state.
        
        Args:
            state: 状态向量
            deterministic: 是否使用确定性策略
            threshold: 预测阈值（默认0.3，优化后用于解决预测过少问题）
        """
        with torch.no_grad():
            logits = self.forward(state)
            probs = torch.sigmoid(logits)
            
            if deterministic:
                # **优化后的预测阈值**：使用0.3（解决预测过少问题）
                action = (probs > threshold).float()
            else:
                # 对于随机策略，也可以使用阈值而不是采样
                action = (probs > threshold).float()
                
            return action.cpu().numpy()
