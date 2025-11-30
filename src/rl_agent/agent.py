import torch
import torch.optim as optim
import numpy as np
from src.rl_agent.model import GuandanModel

class PPOAgent:
    """
    PPO Agent for Guandan.
    """
    def __init__(self, input_dim=115, lr=3e-4, gamma=0.99, clip_ratio=0.2):
        self.model = GuandanModel(input_dim)
        self.optimizer = optim.Adam(self.model.parameters(), lr=lr)
        self.gamma = gamma
        self.clip_ratio = clip_ratio
        
    def act(self, state, deterministic=False):
        """Select an action."""
        with torch.no_grad():
            action, log_prob = self.model.select_action(state, deterministic)
        return action, log_prob
        
    def learn(self, batch):
        """
        Update model using PPO loss.
        Batch is a dictionary of numpy arrays.
        """
        states = torch.FloatTensor(batch['states'])
        actions = torch.LongTensor(batch['actions'])
        old_log_probs = torch.FloatTensor(batch['log_probs'])
        rewards = torch.FloatTensor(batch['rewards'])
        dones = torch.FloatTensor(batch['dones'])
        next_states = torch.FloatTensor(batch['next_states'])
        
        # Calculate Returns and Advantages (Simplified)
        # For true PPO, we need GAE. Here we use simple Monte Carlo or TD targets.
        # Let's use simple TD target for now: r + gamma * V(s')
        
        with torch.no_grad():
            _, next_values = self.model(next_states)
            targets = rewards + self.gamma * next_values.squeeze(-1) * (1 - dones)
            
        # PPO Update Loop
        for _ in range(5): # 5 epochs
            action_logits, values = self.model(states)
            values = values.squeeze(-1)
            
            # Calculate Advantage
            advantages = targets - values.detach()
            
            # Calculate new log probs
            # Reshape actions to match logits shape logic if needed, but Categorical handles it.
            # logits: (B, 54, 3)
            probs = torch.nn.functional.softmax(action_logits, dim=-1)
            dist = torch.distributions.Categorical(probs)
            new_log_probs = dist.log_prob(actions).sum(dim=-1)
            
            # Ratio
            ratio = torch.exp(new_log_probs - old_log_probs)
            
            # Clipped Loss
            surr1 = ratio * advantages
            surr2 = torch.clamp(ratio, 1 - self.clip_ratio, 1 + self.clip_ratio) * advantages
            actor_loss = -torch.min(surr1, surr2).mean()
            
            # Critic Loss
            critic_loss = torch.nn.functional.mse_loss(values, targets)
            
            # Total Loss
            loss = actor_loss + 0.5 * critic_loss
            
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
            
        return loss.item()

    def save(self, path):
        torch.save(self.model.state_dict(), path)
        
    def load(self, path):
        self.model.load_state_dict(torch.load(path))
