import sys
import os
import numpy as np

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.rl_env.guandan_env import GuandanEnv
from src.rl_agent.agent import PPOAgent
from src.knowledge_processor.strategy_encoder import StrategyEncoder

def train_self_play():
    print("Starting Self-Play Training...")
    
    # 1. Init Env & Agent
    env = GuandanEnv()
    agent = PPOAgent()
    strategy_encoder = StrategyEncoder()
    
    # Load pretrained model if exists
    if os.path.exists("models/bc_model_v1.pth"):
        print("Loading pretrained model...")
        agent.load("models/bc_model_v1.pth")
    
    # 2. Training Parameters
    max_episodes = 100 # Short run for verification
    max_timesteps = 200
    update_timestep = 500 # Update policy every n timesteps
    
    timestep = 0
    memory = []
    
    for i_episode in range(1, max_episodes+1):
        state, _ = env.reset()
        current_ep_reward = 0
        
        for t in range(max_timesteps):
            timestep += 1
            
            # Select Action
            action, log_prob = agent.select_action(state)
            
            # Execute
            next_state, reward, done, _, info = env.step(action)
            
            # Shaping Reward
            # Convert action (binary) to card list for encoder
            action_cards = [i for i, x in enumerate(action) if x == 1]
            # Need to reconstruct state dict for encoder (Simplified)
            state_dict = {'current_player': env.engine.current_player, 'hands': env.engine.hands}
            shaping = strategy_encoder.calculate_shaping_reward(state_dict, action_cards)
            
            total_reward = reward + shaping
            
            # Store in memory
            memory.append((state, action, log_prob, total_reward, done))
            
            state = next_state
            current_ep_reward += total_reward
            
            # Update PPO
            if timestep % update_timestep == 0:
                agent.update(memory)
                memory = []
                
            if done:
                break
                
        if i_episode % 10 == 0:
            print(f"Episode {i_episode}, Reward: {current_ep_reward:.2f}")
            
            # Log to Markdown
            with open("TRAINING_LOG.md", "a") as f:
                if i_episode == 10 and not os.path.exists("TRAINING_LOG.md"):
                    f.write("| Episode | Reward | Timesteps |\n")
                    f.write("|---------|--------|-----------|\n")
                f.write(f"| {i_episode} | {current_ep_reward:.2f} | {timestep} |\n")
            
    # 3. Save Model
    os.makedirs("models", exist_ok=True)
    agent.save("models/ppo_model_v1.pth")
    print("Training Complete. Model saved to models/ppo_model_v1.pth")

if __name__ == "__main__":
    train_self_play()
