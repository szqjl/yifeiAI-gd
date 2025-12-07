import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from .model import GuandanPolicyNet

class PPOAgent:
    def __init__(self, input_dim=512, action_dim=512, lr=0.0003, gamma=0.99, eps_clip=0.2, K_epochs=4, prediction_threshold=0.3):
        """
        PPO Agent for Guandan AI
        
        **当前配置（根据2025-12-07评估结果进一步优化）**:
        - prediction_threshold: 0.3（从0.2进一步提高，继续减少预测过多问题）
        - 概率缩放因子: 5.0（在select_action中应用，从7.0进一步降低）
        - 调整原因: 当前数据796样本，预测过多仍占66.3%，需要继续提高阈值和降低缩放
        
        Args:
            input_dim: 状态空间维度（512维，对应512个卡牌索引位置）
            action_dim: 动作空间维度（512维，与状态空间一致，每个维度表示是否选择对应的卡牌）
            prediction_threshold: 预测阈值（默认0.1，最优配置）
        """
        self.prediction_threshold = prediction_threshold  # 最优配置：0.1
        self.gamma = gamma
        self.eps_clip = eps_clip
        self.K_epochs = K_epochs
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.policy = GuandanPolicyNet(input_dim, 256, action_dim).to(self.device)
        self.optimizer = optim.Adam(self.policy.parameters(), lr=lr)
        
        self.policy_old = GuandanPolicyNet(input_dim, 256, action_dim).to(self.device)
        self.policy_old.load_state_dict(self.policy.state_dict())
        
        self.MseLoss = nn.MSELoss()

    def select_action(self, state):
        """
        Select action for a given state.
        Returns: action (numpy), log_prob (float)
        """
        with torch.no_grad():
            state = torch.FloatTensor(state).to(self.device)
            logits = self.policy_old(state)
            
            # For MultiBinary, we treat each card as independent Bernoulli
            # This is a simplification. In reality, card choices are highly correlated.
            # But for V1, this allows the agent to select multiple cards.
            probs = torch.sigmoid(logits)
            
            # **参数调整**：根据2025-12-07评估结果，预测过多仍占66.3%
            # 进一步降低概率缩放因子从7.0到5.0，继续减少预测过多问题
            # 调整历史：10.0(13,409样本) → 7.0(796样本) → 5.0(进一步优化)
            probs = probs * 5.0  # 进一步调整后的缩放因子（从7.0降低到5.0）
            probs = torch.clamp(probs, 0, 1)  # 确保概率值在[0, 1]范围内
            
            # **调整预测阈值**：使用阈值而不是采样
            # 基于自动测试，最优参数组合为：缩放因子5.0 + 阈值0.5
            action = (probs > self.prediction_threshold).float()
            
            # 计算log_prob（用于PPO训练）
            # 注意：这里使用缩放前的原始概率计算log_prob，以保持训练一致性
            original_probs = torch.sigmoid(logits)
            dist = torch.distributions.Bernoulli(original_probs)
            log_prob = dist.log_prob(action).sum() # Sum log probs of all cards
            
            return action.cpu().numpy(), log_prob.item()

    def update(self, memory):
        """
        Update policy using PPO.
        memory: list of (state, action, log_prob, reward, done)
        """
        # Convert memory to tensors
        states = torch.FloatTensor(np.array([t[0] for t in memory])).to(self.device)
        actions = torch.FloatTensor(np.array([t[1] for t in memory])).to(self.device)
        old_log_probs = torch.FloatTensor(np.array([t[2] for t in memory])).to(self.device)
        rewards = torch.FloatTensor(np.array([t[3] for t in memory])).to(self.device)
        dones = torch.FloatTensor(np.array([t[4] for t in memory])).to(self.device)
        
        # Monte Carlo Estimate of Rewards
        returns = []
        discounted_reward = 0
        for reward, is_done in zip(reversed(rewards), reversed(dones)):
            if is_done:
                discounted_reward = 0
            discounted_reward = reward + (self.gamma * discounted_reward)
            returns.insert(0, discounted_reward)
            
        returns = torch.FloatTensor(returns).to(self.device)
        # Normalize returns
        returns = (returns - returns.mean()) / (returns.std() + 1e-7)
        
        # PPO Update
        for _ in range(self.K_epochs):
            # Evaluate old actions and values
            logits = self.policy(states)
            probs = torch.sigmoid(logits)
            dist = torch.distributions.Bernoulli(probs)
            
            log_probs = dist.log_prob(actions).sum(dim=1)
            entropy = dist.entropy().sum(dim=1)
            
            # Ratio
            ratios = torch.exp(log_probs - old_log_probs)
            
            # Surrogate Loss
            surr1 = ratios * returns
            surr2 = torch.clamp(ratios, 1-self.eps_clip, 1+self.eps_clip) * returns
            
            loss = -torch.min(surr1, surr2) - 0.01 * entropy
            
            self.optimizer.zero_grad()
            loss.mean().backward()
            self.optimizer.step()
            
        # Update old policy
        self.policy_old.load_state_dict(self.policy.state_dict())

    def save(self, path):
        torch.save(self.policy.state_dict(), path)

    def load(self, path):
        self.policy.load_state_dict(torch.load(path, map_location=self.device))
        self.policy_old.load_state_dict(self.policy.state_dict())
