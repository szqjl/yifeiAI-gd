import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

class GuandanModel(nn.Module):
    """
    Actor-Critic Model for Guandan.
    
    Input: Game State Vector (115,)
    Output:
        - Actor: 54 * 3 logits (for MultiDiscrete action space)
        - Critic: 1 value (state value)
    """
    def __init__(self, input_dim=115, hidden_dim=256):
        super(GuandanModel, self).__init__()
        
        # Shared Feature Extractor
        self.feature_net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU()
        )
        
        # Actor Head
        # 54 cards, each has 3 options (0, 1, 2)
        self.actor_head = nn.Linear(hidden_dim, 54 * 3)
        
        # Critic Head
        self.critic_head = nn.Linear(hidden_dim, 1)
        
    def forward(self, x):
        features = self.feature_net(x)
        
        # Actor
        action_logits = self.actor_head(features)
        # Reshape to (Batch, 54, 3)
        action_logits = action_logits.view(-1, 54, 3)
        
        # Critic
        state_value = self.critic_head(features)
        
        return action_logits, state_value

    def select_action(self, state, deterministic=False):
        """
        Select action given state.
        Returns: action (np.array), log_prob (torch.tensor)
        """
        state_tensor = torch.FloatTensor(state).unsqueeze(0) # Add batch dim
        action_logits, _ = self.forward(state_tensor)
        
        # Masking invalid actions? 
        # For now, we rely on the environment to punish invalid actions.
        # But we could mask actions that try to play cards we don't have.
        # (This requires passing hand info separately or parsing state).
        # Let's keep it simple: Agent learns to avoid invalid moves.
        
        probs = F.softmax(action_logits, dim=-1)
        
        if deterministic:
            action = torch.argmax(probs, dim=-1)
        else:
            # Sample from categorical distribution for each card
            dist = torch.distributions.Categorical(probs)
            action = dist.sample()
            
            # Calculate log prob
            # Sum log probs of independent actions
            log_prob = dist.log_prob(action).sum(dim=-1)
            
        return action.squeeze(0).numpy(), log_prob
