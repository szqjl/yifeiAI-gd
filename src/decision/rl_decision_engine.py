import torch
import numpy as np
from typing import List, Dict
from src.rl_agent.agent import PPOAgent
# Assuming we have a base class or interface, but for now standalone
# from .base_decision_engine import BaseDecisionEngine 

class RLDecisionEngine:
    def __init__(self, model_path="models/ppo_model_v1.pth"):
        self.agent = PPOAgent()
        try:
            self.agent.load(model_path)
            print(f"RL Engine loaded model from {model_path}")
        except Exception as e:
            print(f"Failed to load RL model: {e}. Using random weights (Not recommended for production).")
            
    def decide(self, data: Dict) -> int:
        """
        Main interface for the client.
        data: Server message containing 'actionList', 'handCards', etc.
        Returns: Index of the selected action in actionList.
        """
        action_list = data.get("actionList", [])
        if not action_list:
            return 0
            
        # Parse state from data
        # Note: data keys might differ from what we assumed. 
        # Client passes 'data' which has 'handCards' (maybe? need to check client code)
        # In yf1_v4.py, handle_notification updates hand cards, but handle_action_request 
        # passes 'data' which has 'actionList'. It might NOT have 'handCards' directly 
        # if it's just the action request.
        # We need to track hand cards in the engine or pass them in.
        # For now, let's assume we need to track state or extract it.
        
        # simplified: just try to match action
        # We need the current hand to construct state. 
        # The client should ideally pass the full state.
        # But for drop-in replacement, we might need to rely on what's in 'data' 
        # or maintain internal state.
        
        # Let's assume 'handCards' is in data or we can't do much.
        # If not, we might need to update client to pass it.
        state_info = {
            'hand': data.get('handCards', []), # This might be missing in 'act' msg
            'table': [], # TODO: Extract from publicInfo
            'history': []
        }
        
        # Get desired cards from RL
        desired_cards = self.get_action(state_info)
        desired_set = set(desired_cards)
        
        # Debug: Print actionList for troubleshooting
        if desired_cards:
            print(f"[RL Debug] Desired cards: {desired_cards}")
            print(f"[RL Debug] Available actions: {[a[2] if len(a) >= 3 else a for a in action_list[:5]]}")  # Show first 5
        
        # Find matching action in actionList
        best_idx = 0
        best_match_score = -1
        
        for i, action in enumerate(action_list):
            # action format: ['Single', '3', ['H3']] or ['PASS', 'PASS', 'PASS']
            if action[0] == 'PASS':
                if not desired_cards: # RL wants to pass
                    return i
                continue
                
            # Extract cards from action
            # Action structure: [Type, Rank, [Cards]]
            if len(action) >= 3:
                action_cards = action[2] if isinstance(action[2], list) else []
                
                # Exact match
                if set(action_cards) == desired_set:
                    return i
                
                # Partial match scoring (fallback)
                if desired_cards and action_cards:
                    match_count = len(set(action_cards) & desired_set)
                    match_score = match_count / max(len(action_cards), len(desired_cards))
                    if match_score > best_match_score:
                        best_match_score = match_score
                        best_idx = i
                    
        # If we found a partial match, use it
        if best_match_score > 0.5:
            print(f"RL desired {desired_cards} - using partial match (score: {best_match_score:.2f}) at index {best_idx}")
            return best_idx
            
        # If no match, fallback to PASS (index 0)
        print(f"RL desired {desired_cards} but not found in actionList. Falling back to 0 (PASS).")
        return 0

    def get_action(self, state_info: Dict) -> List[str]:
        """
        Decide action based on state.
        state_info: Dict containing 'hand', 'table', etc. from the main client.
        Returns: List of card codes (e.g. ['H2', 'S3'])
        """
        # 1. Preprocess State
        # We need to convert the rich state_info into the 512-dim vector expected by the model
        state_vec = self._preprocess_state(state_info)
        
        # 2. Query Agent
        action_binary, _ = self.agent.select_action(state_vec)
        
        # 3. Decode Action
        # Convert binary vector back to card indices, then to card codes
        selected_indices = [i for i, x in enumerate(action_binary) if x == 1]
        selected_cards = self._indices_to_cards(selected_indices, state_info['hand'])
        
        # 4. Validation / Fallback
        # If the model outputs cards we don't have, or an invalid combination
        # We should probably filter or fallback to a rule-based approach.
        # For V5.0, let's just return what the model thinks, but filter for ownership.
        
        # Filter: Only play cards we actually have
        my_hand_set = set(state_info['hand'])
        valid_cards = [c for c in selected_cards if c in my_hand_set]
        
        return valid_cards

    def _preprocess_state(self, state_info):
        """
        Convert client state to RL state vector.
        """
        # Placeholder: Needs to match the encoding used in GuandanEnv / ReplayParser
        obs = np.zeros(512, dtype=np.float32)
        
        # Encode Hand
        for card in state_info['hand']:
            idx = self._card_to_index(card)
            if idx < 512:
                obs[idx] = 1.0
                
        return obs

    def _card_to_index(self, card_code):
        # Simple hash used in training
        return sum(ord(c) for c in card_code) % 54

    def _indices_to_cards(self, indices, current_hand):
        """
        Map indices back to actual cards in hand.
        Since our hash is lossy (modulo 54), this is tricky.
        We need to find a card in hand that matches the index.
        """
        result = []
        hand_copy = list(current_hand)
        
        for idx in indices:
            # Find a card in hand that maps to this index
            found = False
            for card in hand_copy:
                if self._card_to_index(card) == idx:
                    result.append(card)
                    hand_copy.remove(card) # Consume card
                    found = True
                    break
            if not found:
                # Model asked for a card we don't have (or duplicate we don't have enough of)
                pass
                
        return result
