# -*- coding: utf-8 -*-
import torch
import torch.nn as nn
import torch.nn.functional as F

# 修复Windows控制台编码（如果可能）
try:
    from src.utils.encoding_fix import fix_windows_console_encoding
    fix_windows_console_encoding()
except ImportError:
    pass

class GuandanPolicyNet(nn.Module):
    def __init__(self, input_dim=512, hidden_dim=256, output_dim=512, dropout_rate=0.1, 
                 strategy_num_classes=7, enable_strategy_head=True):
        """
        Policy Network for Guandan AI with Multi-Task Learning
        
        Args:
            input_dim: 状态空间维度（512维，对应512个卡牌索引位置）
            hidden_dim: 隐藏层维度
            output_dim: 动作空间维度（512维，与状态空间一致，每个维度表示是否选择对应的卡牌）
            dropout_rate: Dropout比率（用于正则化，防止过拟合）
                          **优化**: 从0.2降到0.1，减少过拟合，提高模型输出概率
            strategy_num_classes: 策略分类类别数（7类：bomb、suppress、protect、control、group、follow、discard）
            enable_strategy_head: 是否启用策略分类头（用于多任务学习）
        """
        super(GuandanPolicyNet, self).__init__()
        
        # 共享特征提取层（fc1和fc2）
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.dropout = nn.Dropout(dropout_rate)
        
        # 动作预测头（原有）
        self.fc3 = nn.Linear(hidden_dim, output_dim)
        
        # 策略分类头（新增，阶段2任务1）
        self.enable_strategy_head = enable_strategy_head
        if enable_strategy_head:
            self.fc_strategy = nn.Linear(hidden_dim, strategy_num_classes)
        
    def forward(self, x, return_strategy=False):
        """
        前向传播
        
        Args:
            x: 输入状态向量 (batch_size, input_dim)
            return_strategy: 是否返回策略分类结果（用于多任务学习）
        
        Returns:
            - 如果return_strategy=False: 返回动作预测logits (batch_size, output_dim)
            - 如果return_strategy=True: 返回(action_logits, strategy_logits)元组
        """
        # 共享特征提取
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        x = F.relu(self.fc2(x))
        x = self.dropout(x)
        
        # 动作预测头
        action_logits = self.fc3(x)
        
        # 策略分类头（如果启用）
        if return_strategy and self.enable_strategy_head:
            strategy_logits = self.fc_strategy(x)
            return action_logits, strategy_logits
        else:
            return action_logits
    
    def get_strategy_probs(self, x):
        """
        获取策略分类概率分布
        
        Args:
            x: 输入状态向量 (batch_size, input_dim)
        
        Returns:
            策略类型概率分布 (batch_size, strategy_num_classes)
        """
        if not self.enable_strategy_head:
            raise ValueError("策略分类头未启用，请设置enable_strategy_head=True")
        
        with torch.no_grad():
            # 共享特征提取
            x = F.relu(self.fc1(x))
            x = self.dropout(x)
            x = F.relu(self.fc2(x))
            x = self.dropout(x)
            
            # 策略分类头
            strategy_logits = self.fc_strategy(x)
            strategy_probs = F.softmax(strategy_logits, dim=1)
            
            return strategy_probs.cpu().numpy()

    def get_action(self, state, deterministic=False, threshold=0.3, scaling_factor=5.0):
        """
        Select action given state.
        
        **基线评估参数（阶段0验证的标准）**:
        - 概率缩放因子: 5.0（阶段0基线参数）
        - 预测阈值: 0.3（阶段0基线参数）
        - 基线性能: 完全匹配准确率37.31%，卡牌级别准确率96.73%
        - 数据量: 796样本（34个对局）
        
        **重要说明**:
        - 所有阶段的模型评估必须使用此基线参数（阈值0.3，缩放因子5.0）作为统一标尺
        - 不能为了提升准确率而调整评估参数
        - 评估参数应该以基线评估参数为参考，而不是为了准确率去调基线评估的参数
        
        Args:
            state: 状态向量（numpy数组或torch.Tensor）
            deterministic: 是否使用确定性策略
            threshold: 预测阈值（默认0.3，基线评估参数）
            scaling_factor: 概率缩放因子（默认5.0，基线评估参数）
        """
        with torch.no_grad():
            # 确保输入是torch.Tensor
            if not isinstance(state, torch.Tensor):
                state = torch.FloatTensor(state)
            else:
                state = state.clone().detach()
            
            # 确保state在正确的设备上
            if next(self.parameters()).is_cuda:
                state = state.cuda()
            
            # 使用forward方法，不返回策略分类结果（保持向后兼容）
            logits = self.forward(state, return_strategy=False)
            probs = torch.sigmoid(logits)
            
            # **基线评估参数**：使用阶段0验证的标准参数
            # 缩放因子5.0，阈值0.3（阶段0基线，完全匹配准确率37.31%）
            probs = probs * scaling_factor  # 基线缩放因子5.0
            probs = torch.clamp(probs, 0, 1)  # 确保概率值在[0, 1]范围内
            
            if deterministic:
                # **基线预测阈值**：使用0.3（阶段0基线参数）
                action = (probs > threshold).float()
            else:
                # 对于随机策略，也可以使用阈值而不是采样
                action = (probs > threshold).float()
                
            return action.cpu().numpy()
