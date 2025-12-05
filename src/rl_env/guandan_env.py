import gymnasium as gym
from gymnasium import spaces
import numpy as np
from .game_engine import GameEngine

class GuandanEnv(gym.Env):
    metadata = {'render.modes': ['human']}

    def __init__(self):
        super(GuandanEnv, self).__init__()
        self.engine = GameEngine()
        
        # Action Space: 
        # **关键修复**：动作空间必须是512维，与状态空间一致
        # 每个维度对应一个卡牌索引位置（0-59是有效卡牌，60-511保留用于扩展）
        # 1 = 选择该索引对应的卡牌, 0 = 不选择
        self.action_space = spaces.MultiBinary(512) 
        
        # Observation Space:
        # 1. My Hand (108 binary)
        # 2. Table Cards (108 binary * History Depth)
        # 3. Teammate Hand Probabilities (108 float)
        # 4. Opponent Hand Probabilities (108 float * 2)
        # Total size ~ 1000+
        self.observation_space = spaces.Box(low=0, high=1, shape=(512,), dtype=np.float32)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        state = self.engine.reset()
        return self._encode_state(state), {}

    def step(self, action):
        # Convert MultiBinary action to card list
        # action is array of 0/1 of length 512
        # 只使用有效索引（0-59）对应的卡牌
        valid_indices = [i for i, x in enumerate(action) if x == 1 and i < 60]
        selected_cards = valid_indices  # 这里需要将索引转换为实际卡牌，暂时使用索引
        
        try:
            next_state, reward, done, info = self.engine.step(selected_cards)
            
            # Reward Shaping
            if done:
                # Check if my team won
                pass
                
            return self._encode_state(next_state), reward, done, False, info
            
        except ValueError as e:
            # Invalid move
            # Penalty for invalid move
            return self._encode_state(self.engine.get_state()), -10, False, False, {"error": str(e)}

    def _encode_state(self, state):
        """
        编码游戏状态为512维向量
        必须与 rl_decision_engine.py 中的 _preprocess_state 保持一致！
        """
        obs = np.zeros(512, dtype=np.float32)
        
        # 获取当前玩家的手牌
        current_player = state.get('current_player', 0)
        hands = state.get('hands', {})
        hand_cards = hands.get(current_player, [])
        
        # 使用与推理代码相同的编码方式
        def card_to_index(card_code):
            """与 rl_decision_engine.py 中的编码方式完全一致"""
            suit_map = {'S': 0, 'H': 1, 'C': 2, 'D': 3}
            rank_map = {
                '2': 0, '3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6, '9': 7,
                'T': 8, 'J': 9, 'Q': 10, 'K': 11, 'A': 12,
                'B': 13,  # 小王
                'R': 14   # 大王
            }
            if len(card_code) >= 2:
                suit = card_code[0]
                rank = card_code[1]
                suit_val = suit_map.get(suit, 0)
                rank_val = rank_map.get(rank, 0)
                idx = suit_val * 15 + rank_val
                return min(idx, 59)  # 确保在0-59范围内
            return 0
        
        # 编码手牌
        for card in hand_cards:
            idx = card_to_index(card)
            if idx < 512:
                obs[idx] = 1.0
        
        # TODO: 编码其他信息（桌牌、历史、队友状态等）
        # 目前只编码手牌，后续可以扩展
        
        return obs

    def render(self, mode='human'):
        print(f"Current Player: {self.engine.current_player}")
        print(f"Table: {self.engine.table_cards}")
