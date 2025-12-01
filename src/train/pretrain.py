import sys
import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np

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
        
        # Convert state_dict to vector (Simplified)
        # In real impl, we need a robust encoder
        # Here we just use a random vector for demonstration of pipeline
        state_vec = np.zeros(512, dtype=np.float32)
        
        # Encode Hand (First 54 dims)
        # Need card mapping logic. Reusing simple logic:
        # Just hashing card strings to indices for now
        for card in state_dict['hand']:
            # Simple hash: sum of ASCII values % 54
            idx = sum(ord(c) for c in card) % 54
            state_vec[idx] = 1.0
            
        # Convert action_cards to vector (Target)
        action_vec = np.zeros(108, dtype=np.float32)
        for card in action_cards:
            idx = sum(ord(c) for c in card) % 54 # Same hash
            action_vec[idx] = 1.0
            
        return torch.FloatTensor(state_vec), torch.FloatTensor(action_vec)

def train_bc():
    print("Starting Behavior Cloning Pre-training...")
    
    # 1. Load Data
    parser = ReplayParser("game_records")
    replays = parser.load_replays()
    raw_data = parser.extract_training_data(replays)
    print(f"Loaded {len(raw_data)} samples.")
    
    if len(raw_data) == 0:
        print("No data found. Exiting.")
        return

    dataset = GuandanDataset(raw_data)
    dataloader = DataLoader(dataset, batch_size=32, shuffle=True)
    
    # 2. Setup Model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    model = GuandanPolicyNet().to(device)
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.BCEWithLogitsLoss() # Multi-label classification
    
    # 3. Training Loop
    epochs = 5
    for epoch in range(epochs):
        total_loss = 0
        for states, actions in dataloader:
            states, actions = states.to(device), actions.to(device)
            
            optimizer.zero_grad()
            logits = model(states)
            loss = criterion(logits, actions)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            
        avg_loss = total_loss / len(dataloader)
        print(f"Epoch {epoch+1}/{epochs}, Loss: {avg_loss:.4f}")
        
    # 4. Save Model
    os.makedirs("models", exist_ok=True)
    torch.save(model.state_dict(), "models/bc_model_v1.pth")
    print("Model saved to models/bc_model_v1.pth")

if __name__ == "__main__":
    train_bc()
