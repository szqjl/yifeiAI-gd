import json
import os
import ast
from typing import List, Dict, Tuple
import numpy as np

class ReplayParser:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        
    def load_replays(self) -> List[Dict]:
        """Load all JSON replay files from the directory."""
        replays = []
        if not os.path.exists(self.data_dir):
            print(f"Warning: Directory {self.data_dir} does not exist.")
            return []
            
        for filename in os.listdir(self.data_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.data_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        replays.append(data)
                except Exception as e:
                    print(f"Error loading {filename}: {e}")
        return replays

    def parse_action_string(self, action_str: str) -> Tuple[str, List[str]]:
        """
        Parse action string like "['Straight', '6', ['C6', 'S7', 'S8', 'S9', 'HT']]"
        Returns (Type, CardList)
        """
        try:
            # Use ast.literal_eval to safely parse the string representation of list
            parsed = ast.literal_eval(action_str)
            if parsed[0] == 'PASS':
                return 'PASS', []
            return parsed[0], parsed[2]
        except:
            # Handle potential format variations
            if 'PASS' in action_str:
                return 'PASS', []
            return 'UNKNOWN', []

    def extract_training_data(self, replays: List[Dict]):
        """
        Process replays to generate (State, Action) pairs.
        Note: This is a simplified version. A full version needs to reconstruct 
        the exact hand of the player at each step.
        """
        dataset = []
        
        for replay in replays:
            # We need to track the state of the game
            # Initial hands are given for the recording player (player_id)
            # But 'actions' contains moves from ALL players.
            # To reconstruct the state for ANY player, we need to know their initial hands.
            # The current JSON log format might only contain 'initial_hand' for the recording player.
            # Let's check if we can deduce others or if we only train on the recording player.
            
            # For V1, let's only train on the recording player's moves since we know their hand.
            hero_id = replay.get('player_id')
            hero_hand = set(replay.get('initial_hand', []))
            
            # We need to simulate the game flow to remove cards from hand
            # and build the history/table state.
            
            history = []
            
            for action_log in replay.get('actions', []):
                actor_pos = action_log['cur_pos']
                action_str = action_log['cur_action']
                action_type, cards_played = self.parse_action_string(action_str)
                
                # If it's the Hero's turn, record the state BEFORE the action
                if actor_pos == hero_id:
                    # Construct Observation
                    # State = (MyHand, History, ...)
                    # For now, just storing raw data
                    state = {
                        'hand': list(hero_hand),
                        'history': history[-10:] # Last 10 moves
                    }
                    
                    # Target Action
                    target = cards_played
                    
                    dataset.append((state, target))
                    
                    # Update Hero's hand
                    for card in cards_played:
                        if card in hero_hand:
                            hero_hand.remove(card)
                
                # Update History
                history.append({
                    'player': actor_pos,
                    'action': cards_played
                })
                
        return dataset

if __name__ == "__main__":
    # Test
    parser = ReplayParser("game_records")
    replays = parser.load_replays()
    print(f"Loaded {len(replays)} replays")
    data = parser.extract_training_data(replays)
    print(f"Extracted {len(data)} training samples")
    if len(data) > 0:
        print("Sample 0:", data[0])
