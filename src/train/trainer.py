import sys
import os
import numpy as np
import torch
import time
from collections import deque

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.rl_env.guandan_env import GuandanEnv
from src.rl_agent.agent import PPOAgent

def train(max_episodes=1000, batch_size=64):
    """
    Training loop for Guandan AI.
    """
    env = GuandanEnv()
    # **关键修复**：确保action_dim与推理代码一致（512维）
    agent = PPOAgent(input_dim=512, action_dim=512)
    
    # Replay Buffer (Simple list for PPO batch)
    batch = {
        'states': [],
        'actions': [],
        'log_probs': [],
        'rewards': [],
        'dones': [],
        'next_states': []
    }
    
    scores = deque(maxlen=100)
    
    print(f"Starting training for {max_episodes} episodes...")
    
    for episode in range(max_episodes):
        state, _ = env.reset()
        done = False
        score = 0
        
        while not done:
            # Select Action
            action, log_prob = agent.select_action(state)
            
            # Step
            next_state, reward, done, _, info = env.step(action)
            
            # Store transition
            batch['states'].append(state)
            batch['actions'].append(action)
            batch['log_probs'].append(log_prob.item()) # Store scalar
            batch['rewards'].append(reward)
            batch['dones'].append(done)
            batch['next_states'].append(next_state)
            
            state = next_state
            score += reward
            
            # Train if batch is full
            if len(batch['states']) >= batch_size:
                # Convert to memory format for PPO update
                # PPOAgent.update expects: list of (state, action, log_prob, reward, done)
                memory = []
                for i in range(len(batch['states'])):
                    memory.append((
                        batch['states'][i],
                        batch['actions'][i],
                        batch['log_probs'][i],
                        batch['rewards'][i],
                        batch['dones'][i]
                    ))
                agent.update(memory)
                
                # Clear batch
                for k in batch:
                    batch[k] = []
                    
        scores.append(score)
        avg_score = np.mean(scores)
        
        if (episode + 1) % 10 == 0:
            print(f"Episode {episode+1}/{max_episodes} | Score: {score:.2f} | Avg Score: {avg_score:.2f}")
            
        if (episode + 1) % 100 == 0:
            agent.save(f"models/ppo_guandan_ep{episode+1}.pth")
            
    print("Training Complete!")
    agent.save("models/ppo_guandan_final.pth")

if __name__ == "__main__":
    # Create models directory if not exists
    os.makedirs("models", exist_ok=True)
    train()
