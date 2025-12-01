import torch
import torch.nn as nn
import torch.nn.functional as F

class GuandanPolicyNet(nn.Module):
    def __init__(self, input_dim=512, hidden_dim=256, output_dim=108):
        super(GuandanPolicyNet, self).__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, output_dim)
        
    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        logits = self.fc3(x)
        # Output logits for MultiBinary action selection
        # We will use BCEWithLogitsLoss for training if treating as multi-label classification
        # Or we can use it to sample actions
        return logits

    def get_action(self, state, deterministic=False):
        """
        Select action given state.
        """
        with torch.no_grad():
            logits = self.forward(state)
            probs = torch.sigmoid(logits)
            
            if deterministic:
                action = (probs > 0.5).float()
            else:
                action = torch.bernoulli(probs)
                
            return action.cpu().numpy()
