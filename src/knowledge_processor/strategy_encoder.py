from typing import List

class StrategyEncoder:
    def __init__(self):
        pass
        
    def calculate_shaping_reward(self, state_dict: dict, action_cards: List[int]) -> float:
        """
        Calculate additional reward based on strategy rules.
        state_dict: {'hand': [...], 'table_cards': [...]}
        action_cards: List of card IDs played
        """
        reward = 0.0
        
        # Rule 1: Validity Check (Big Penalty for Invalid Moves)
        # This is handled by the Env usually, but we can reinforce it here
        # Assuming action_cards are valid for this check context
        
        # Rule 2: Bomb Conservation
        # If player breaks a bomb (e.g. has 4 Kings, plays 1 King), penalty
        # Need to analyze hand structure.
        # Simplified check:
        hand = state_dict.get('hands', {}).get(state_dict.get('current_player'), [])
        # TODO: Implement full hand analysis to detect bombs
        
        # Rule 3: Empty Action (Pass)
        # If passing when you could beat the table, small penalty (timidity)
        # If passing when you are leader, big penalty (illegal)
        if not action_cards:
            # Check if leader
            # This logic should be in GameEngine, but here we shape behavior
            pass
            
        # Rule 4: Finishing Hand
        # Big reward for finishing
        if len(action_cards) == len(hand):
            reward += 5.0
            
        return reward

    def analyze_hand_structure(self, hand: List[int]):
        """
        Analyze hand to find Bombs, Straights, etc.
        """
        pass
