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
        # Complex issue for card games. 
        # Option 1: Discrete(All Possible Moves) - Too large
        # Option 2: MultiDiscrete([Card1, Card2...]) - Hard to validate
        # Option 3: Masked Discrete - Select from legal moves list
        # For V1, let's assume a simplified action space or just output raw card indices
        # Let's use a fixed size vector for card selection (54*2 = 108 cards)
        # 1 = Play, 0 = Keep
        self.action_space = spaces.MultiBinary(108) 
        
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
        # action is array of 0/1 of length 108
        selected_cards = [i for i, x in enumerate(action) if x == 1]
        
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
        # Placeholder encoding
        # Real implementation needs to serialize hands and table info
        obs = np.zeros(512, dtype=np.float32)
        # Fill obs...
        return obs

    def render(self, mode='human'):
        print(f"Current Player: {self.engine.current_player}")
        print(f"Table: {self.engine.table_cards}")
