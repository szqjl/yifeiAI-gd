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
    # **关键修复**：确保action_dim与推理代码一致（512维）
    agent = PPOAgent(input_dim=512, action_dim=512)
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
            
            # Shaping Reward（增强版：包含组牌、顺牌、跟牌、控牌策略奖励）
            # Convert action (binary) to card list for encoder
            action_cards_indices = [i for i, x in enumerate(action) if x == 1]
            
            # 将索引转换为卡牌代码（需要从engine获取）
            state = env.engine.get_state()
            current_player = state.get('current_player', 0)
            hands = state.get('hands', {})
            hand_cards = hands.get(current_player, [])
            
            # 简化：使用索引对应的卡牌（实际应该从engine获取卡牌映射）
            action_cards = []
            if action_cards_indices:
                # 从手牌中选择对应索引的卡牌（简化处理）
                for idx in action_cards_indices:
                    if idx < len(hand_cards):
                        action_cards.append(hand_cards[idx])
            
            # 判断动作类型（简化：根据卡牌数量判断）
            action_type = "PASS"
            if len(action_cards) == 1:
                action_type = "Single"
            elif len(action_cards) == 2:
                action_type = "Pair"
            elif len(action_cards) == 3:
                action_type = "Trips"
            elif len(action_cards) >= 5:
                action_type = "Straight"  # 简化：可能是顺子或其他
            
            # 判断游戏阶段
            opponent_rest_cards = []
            for i in range(4):
                if i != current_player:
                    opponent_rest_cards.append(len(hands.get(i, [])))
            min_opponent_cards = min(opponent_rest_cards) if opponent_rest_cards else 27
            
            if min_opponent_cards >= 20:
                game_phase = "opening"
            elif min_opponent_cards >= 10:
                game_phase = "mid"
            else:
                game_phase = "endgame"
            
            # 构建状态字典
            state_dict = {
                'current_player': current_player,
                'hands': hands,
                'last_action': info.get('last_action', {})
            }
            
            # 计算shaping reward（增强版）
            shaping = strategy_encoder.calculate_shaping_reward(
                state_dict=state_dict,
                action_cards=action_cards,
                action_type=action_type,
                game_phase=game_phase,
                cur_rank="2"  # 简化：使用默认级牌
            )
            
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
