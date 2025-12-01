import random
from typing import List, Tuple, Dict, Optional
from collections import Counter
import itertools

# Card Constants
# 2-A: 0-12
# Small Joker: 52, Big Joker: 53
# Suits are implicit in 0-51 (0-12: Spades, 13-25: Hearts, 26-38: Clubs, 39-51: Diamonds) - SIMPLIFIED for logic
# Actually for Guandan, rank matters more.
# Let's map 0-53 to Ranks 2-Joker for easier logic.
# 2,3,4,5,6,7,8,9,10,J,Q,K,A -> 0-12
# Level Card (Current Level) -> Special handling needed?
# For V1 Engine, let's stick to standard ranking first, then add Level Card logic.
# Standard Rank Order: 2,3,4,5,6,7,8,9,10,J,Q,K,A, Small, Big
# Values: 2=0, ..., A=12, Small=13, Big=14

class GameEngine:
    def __init__(self, level_card_rank: int = 0):
        """
        Initialize the game engine.
        :param level_card_rank: The rank of the current level card (0=2, 12=A).
        """
        self.level_card_rank = level_card_rank
        # 4 Players: 0, 1, 2, 3. Team 0&2, Team 1&3.
        self.hands = {0: [], 1: [], 2: [], 3: []}
        self.current_player = 0
        self.history = []
        self.table_cards = [] # (player_id, cards, type, value)
        self.pass_count = 0
        self.finished_players = []
        self.rank_map = self._init_rank_map()

    def _init_rank_map(self):
        # Maps internal card ID (0-53) to Logic Rank (0-15)
        # 0-51: 4 suits of 13 cards.
        # 0-12: 2-A
        # 52: Small Joker (14)
        # 53: Big Joker (15)
        # Level Card (Heart) -> 13 (Wild/Special) - Simplified for now: Level Card is just highest non-joker
        rank_map = {}
        for i in range(52):
            base_rank = i % 13
            if base_rank == self.level_card_rank:
                # Level card is higher than A (12) but lower than Joker (14)
                logic_rank = 13 
            else:
                # Adjust for level card being pulled out
                # e.g. if Level is 5 (rank 3), then 2,3,4,6...
                # Actually, standard Guandan order: 2,3,4,5,6,7,8,9,10,J,Q,K,A
                # If 5 is level, order: 2,3,4,6,7,8,9,10,J,Q,K,A, 5, Small, Big
                if base_rank < self.level_card_rank:
                    logic_rank = base_rank
                else:
                    logic_rank = base_rank # Keep original relative order for now, handle level skip later
                    # Wait, if 5 is level, 6 is > 4.
                    # Let's use a simpler static value system for now and refine.
                    pass
            
            # RE-DESIGN: Use a static value table based on level_card_rank
            # 2=2, ... A=14.
            # Level Card = 15.
            # Small Joker = 16.
            # Big Joker = 17.
            pass
        return {} # Placeholder

    def get_card_value(self, card_id: int) -> int:
        """
        Get the logical value of a card for comparison.
        """
        if card_id == 53: return 17 # Big Joker
        if card_id == 52: return 16 # Small Joker
        
        base_rank = card_id % 13 # 0(2) - 12(A)
        
        # Adjust base_rank to 2-14 scale
        value = base_rank + 2 
        
        if base_rank == self.level_card_rank:
            # Heart Level Card is highest level card? For now treat all level cards same
            return 15
            
        return value

    def reset(self):
        """Shuffle and deal cards."""
        deck = list(range(54)) * 2 # Two decks
        random.shuffle(deck)
        self.hands = {
            0: sorted(deck[0:27]),
            1: sorted(deck[27:54]),
            2: sorted(deck[54:81]),
            3: sorted(deck[81:108])
        }
        self.current_player = 0 # Randomize or fixed?
        self.history = []
        self.table_cards = []
        self.pass_count = 0
        self.finished_players = []
        return self.get_state()

    def get_state(self):
        """Return current game state."""
        return {
            'hands': self.hands,
            'current_player': self.current_player,
            'table_cards': self.table_cards,
            'finished_players': self.finished_players
        }

    def step(self, action: List[int]):
        """
        Execute an action (play cards).
        :param action: List of card IDs. Empty list for PASS.
        """
        player = self.current_player
        
        if not action: # PASS
            if self.pass_count >= 3:
                # Cannot pass if you are the leader (everyone else passed)
                # Or if new round
                if not self.table_cards or self.table_cards[-1][0] == player:
                     raise ValueError("Cannot pass when leading")
            
            self.pass_count += 1
            self.history.append((player, [], "PASS"))
            
            # Move to next player
            self._next_player()
            
            # If 3 passes, clear table (new round)
            # Note: Need to handle finished players (they auto-pass)
            active_players = 4 - len(self.finished_players)
            # Logic for clearing table needs to be robust for finished players
            if self.pass_count >= active_players - 1:
                 # Leader logic here
                 pass
            
            return self.get_state(), 0, False, {}

        # PLAY CARDS
        # 1. Validate ownership
        if not all(c in self.hands[player] for c in action):
            raise ValueError("Player does not have these cards")
            
        # 2. Validate Rule (is_legal)
        # TODO: Implement full rule check
        
        # 3. Execute
        for c in action:
            self.hands[player].remove(c)
            
        self.pass_count = 0
        self.table_cards.append((player, action, "UNKNOWN_TYPE", 0)) # Need type recognition
        
        # Check Win
        if not self.hands[player]:
            self.finished_players.append(player)
            
        done = len(self.finished_players) >= 3 # Game ends when 3 players finish (or team logic)
        
        self._next_player()
        
        return self.get_state(), 0, done, {}

    def _next_player(self):
        self.current_player = (self.current_player + 1) % 4
        while self.current_player in self.finished_players:
             self.current_player = (self.current_player + 1) % 4
