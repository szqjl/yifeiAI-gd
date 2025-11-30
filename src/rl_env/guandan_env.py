import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import List, Dict, Optional
from src.rl_env.game_engine import GameEngine

class GuandanEnv(gym.Env):
    """
    Gymnasium environment for Guandan.
    
    Action Space: MultiBinary(54) - Select cards to play.
    Observation Space: Box(low=0, high=2, shape=(115,)) - Game state.
    """
    metadata = {"render_modes": ["human"]}

    def __init__(self, rank: str = '2'):
        self.engine = GameEngine(rank=rank)
        
        # Action Space: 54 bits (one for each unique card type)
        # Note: Guandan has 2 decks, so we have 108 cards, but only 54 unique types.
        # We map index 0-53 to the unique cards.
        # If agent selects index i, we try to play 1 instance of that card.
        # If agent wants to play PAIR, it's tricky with MultiBinary if we map to unique types.
        # Better: MultiDiscrete([3] * 54)? (0, 1, or 2 of each card).
        # Let's use MultiDiscrete([3] * 54).
        self.action_space = spaces.MultiDiscrete([3] * 54)
        
        # Observation Space
        # 0-53: My Hand (0-2)
        # 54-107: Last Play Cards (0-2)
        # 108-111: Num Cards Remaining for P0, P1, P2, P3
        # 112: Current Rank (Integer 2-14)
        # 113: Self Rank
        # 114: Oppo Rank
        self.observation_space = spaces.Box(low=0, high=27, shape=(115,), dtype=np.float32)
        
        self.card_map = self._create_card_map()
        self.inv_card_map = {v: k for k, v in self.card_map.items()}

    def _create_card_map(self) -> Dict[int, str]:
        """Map index 0-53 to card strings like 'H2', 'S2'."""
        suits = ['S', 'H', 'C', 'D']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
        mapping = {}
        idx = 0
        for r in ranks:
            for s in suits:
                mapping[idx] = s + r
                idx += 1
        mapping[52] = 'SB'
        mapping[53] = 'HR'
        return mapping

    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None):
        super().reset(seed=seed)
        self.engine.reset()
        return self._get_obs(), {}

    def step(self, action):
        """
        Action is an array of 54 integers (0, 1, 2).
        """
        # Convert action to list of cards
        card_list = []
        for i, count in enumerate(action):
            if count > 0:
                card_name = self.card_map[i]
                card_list.extend([card_name] * count)
        
        # Execute in engine
        next_state_dict, reward, done, info = self.engine.step(card_list)
        
        # Check if it was invalid
        if info.get("error"):
            # Penalize invalid moves heavily
            reward = -10
            # We don't end the episode, but we might force a PASS or random move?
            # For now, just return same state and let agent try again (or learn to avoid).
            # But in a real game, invalid move might forfeit or be ignored.
            # Let's just return.
            pass
            
        return self._get_obs(), reward, done, False, info

    def _get_obs(self) -> np.ndarray:
        state = self.engine.get_state()
        player = state['current_player']
        hand = state['hands'][player]
        
        obs = np.zeros(115, dtype=np.float32)
        
        # 1. My Hand
        for card in hand:
            idx = self._get_card_idx(card)
            if idx is not None:
                obs[idx] += 1
                
        # 2. Last Play
        if state['last_play']:
            last_p, last_type, last_cards = state['last_play']
            for card in last_cards:
                idx = self._get_card_idx(card)
                if idx is not None:
                    obs[54 + idx] += 1
                    
        # 3. Num Cards Remaining
        for i in range(4):
            obs[108 + i] = len(state['hands'][i])
            
        # 4. Ranks (Simplified mapping)
        rank_val = self.engine._card_sort_key('H' + state['rank']) # Rough approx
        obs[112] = rank_val
        obs[113] = rank_val # Self rank (placeholder)
        obs[114] = rank_val # Oppo rank (placeholder)
        
        return obs

    def _get_card_idx(self, card: str) -> int:
        # Reverse lookup
        # Need to handle suits/ranks correctly.
        # My map is S2, H2, C2, D2...
        # If card is 'H2', it should match.
        for k, v in self.card_map.items():
            if v == card:
                return k
        return None

