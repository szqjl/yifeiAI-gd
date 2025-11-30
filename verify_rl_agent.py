import sys
import os
import torch
import numpy as np

# Add project root to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.rl_agent.agent import PPOAgent

def test_agent():
    print("Testing PPOAgent...")
    agent = PPOAgent()
    
    # Test Act
    state = np.random.rand(115).astype(np.float32)
    action, log_prob = agent.act(state)
    
    print(f"Action Shape: {action.shape}")
    print(f"Log Prob: {log_prob}")
    
    assert action.shape == (54,)
    
    # Test Learn
    batch = {
        'states': np.random.rand(10, 115).astype(np.float32),
        'actions': np.random.randint(0, 3, (10, 54)),
        'log_probs': np.random.rand(10).astype(np.float32),
        'rewards': np.random.rand(10).astype(np.float32),
        'dones': np.zeros(10).astype(np.float32),
        'next_states': np.random.rand(10, 115).astype(np.float32)
    }
    
    loss = agent.learn(batch)
    print(f"Loss: {loss}")
    
    print("PPOAgent Tests Passed!")

if __name__ == "__main__":
    test_agent()
