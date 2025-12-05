import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from .model import GuandanPolicyNet

class PPOAgent:
    def __init__(self, input_dim=512, action_dim=512, lr=0.0003, gamma=0.99, eps_clip=0.2, K_epochs=4, prediction_threshold=0.3):
        """
        PPO Agent for Guandan AI
        
        Args:
            input_dim: 状态空间维度（512维，对应512个卡牌索引位置）
            action_dim: 动作空间维度（512维，与状态空间一致，每个维度表示是否选择对应的卡牌）
            prediction_threshold: 预测阈值（默认0.3，优化后用于解决预测过少问题）
        """
        self.prediction_threshold = prediction_threshold  # 默认0.3，优化后用于解决预测过少问题
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
            
            # **调整预测阈值**：使用阈值而不是采样
            # 根据test_threshold.py测试，0.4是最优阈值（完全匹配准确率23.81%）
            # 0.3时预测过多（准确率1.59%），0.5时预测过少（准确率相同但差异更大）
            action = (probs > self.prediction_threshold).float()
            
            # 计算log_prob（用于PPO训练）
            dist = torch.distributions.Bernoulli(probs)
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
