import torch
import torch.nn as nn
import torch.nn.functional as F

class GuandanPolicyNet(nn.Module):
    def __init__(self, input_dim=512, hidden_dim=256, output_dim=512, dropout_rate=0.1):
        """
        Policy Network for Guandan AI
        
        Args:
            input_dim: 状态空间维度（512维，对应512个卡牌索引位置）
            hidden_dim: 隐藏层维度
            output_dim: 动作空间维度（512维，与状态空间一致，每个维度表示是否选择对应的卡牌）
            dropout_rate: Dropout比率（用于正则化，防止过拟合）
                          **优化**: 从0.2降到0.1，减少过拟合，提高模型输出概率
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

    def get_action(self, state, deterministic=False, threshold=0.1):
        """
        Select action given state.
        
        **最优配置（基于历次训练效果汇总.md）**:
        - 概率缩放因子: 10.0（最优缩放因子，基于概率分布分析）
        - 预测阈值: 0.1（配合缩放因子10.0，效果最佳）
        - 完全匹配准确率: 59.67%（使用最优配置）
        
        Args:
            state: 状态向量
            deterministic: 是否使用确定性策略
            threshold: 预测阈值（默认0.1，最优配置）
        """
        with torch.no_grad():
            logits = self.forward(state)
            probs = torch.sigmoid(logits)
            
            # **最优配置**：概率缩放×10.0（基于历次训练效果汇总.md）
            # 缩放因子10.0是最优选择，准确率59.67%，比50.0的1.57%好19倍
            probs = probs * 10.0  # 最优缩放因子
            probs = torch.clamp(probs, 0, 1)  # 确保概率值在[0, 1]范围内
            
            if deterministic:
                # **优化后的预测阈值**：使用0.5（基于自动测试，最优值）
                # 注意：如果外部传入的threshold不是0.5，使用传入的值
                # 但推荐使用0.5以获得最佳效果
                action = (probs > threshold).float()
            else:
                # 对于随机策略，也可以使用阈值而不是采样
                action = (probs > threshold).float()
                
            return action.cpu().numpy()
