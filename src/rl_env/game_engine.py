import random
from typing import List, Dict, Tuple, Optional
import copy
from src.game_logic.hand_combiner import HandCombiner

class GameEngine:
    """
    A pure logic game engine for Guandan.
    Manages the state of the game, validates moves, and determines the winner.
    """
    def __init__(self, rank: str = '2'):
        self.rank = rank
        self.combiner = HandCombiner()
        self.reset()

    def reset(self):
        """Initialize a new game."""
        # 1. Create Deck (Two decks of cards)
        self.deck = self._create_deck()
        random.shuffle(self.deck)

        # 2. Deal Cards (27 cards per player, 4 players)
        self.hands = {
            0: sorted(self.deck[0:27], key=self._card_sort_key),
            1: sorted(self.deck[27:54], key=self._card_sort_key),
            2: sorted(self.deck[54:81], key=self._card_sort_key),
            3: sorted(self.deck[81:108], key=self._card_sort_key)
        }
        
        # 3. Game State
        self.current_player = 0  # Start with player 0 (randomize later?)
        self.last_play = None    # (player_id, action_type, cards)
        self.pass_count = 0      # Number of consecutive passes
        self.finished_players = [] # Order of players who finished
        self.history = []        # Log of actions

    def _create_deck(self) -> List[str]:
        """Create a double deck of cards."""
        suits = ['S', 'H', 'C', 'D']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
        deck = [s + r for s in suits for r in ranks] * 2
        deck += ['SB', 'HR'] * 2  # Small Joker (Black), Big Joker (Red) - 2 of each
        return deck

    def _card_sort_key(self, card: str) -> int:
        """Helper to sort cards for display/logic."""
        # Value map for sorting
        card_val = {
            "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "T": 10, "J": 11,
            "Q": 12, "K": 13, "A": 14, "B": 16, "R": 17
        }
        # Adjust for Level Card (Rank)
        card_val[self.rank] = 15
        
        if len(card) == 2:
            return card_val.get(card[1], 0)
        return 0

    def get_state(self) -> Dict:
        """Return the current game state."""
        return {
            'hands': self.hands,
            'current_player': self.current_player,
            'last_play': self.last_play,
            'pass_count': self.pass_count,
            'finished_players': self.finished_players,
            'rank': self.rank
        }

    def step(self, action: List[str]) -> Tuple[Dict, float, bool, Dict]:
        """
        Execute an action for the current player.
        
        Args:
            action: List of card codes (e.g., ['H2', 'S2']) or [] for PASS.
            
        Returns:
            next_state, reward, done, info
        """
        player = self.current_player
        
        # 1. Validate Action
        if not self._is_legal(player, action):
            # For RL training, we might want to return a large negative reward and NOT end the episode,
            # or end it. Here we'll return negative reward and continue (or let agent retry).
            # But standard Gym env usually steps.
            # Let's return negative reward and NOT change state (invalid move).
            return self.get_state(), -10, False, {"error": "Illegal move"}

        # 2. Execute Action
        if not action: # PASS
            self.pass_count += 1
            self.history.append((player, 'PASS', []))
        else:
            self.pass_count = 0
            # Remove cards from hand
            for card in action:
                if card in self.hands[player]:
                    self.hands[player].remove(card)
            
            # Identify card type
            card_type = self._get_action_type(action)
            self.last_play = (player, card_type, action)
            self.history.append((player, card_type, action))

        # 3. Check Win Condition
        if len(self.hands[player]) == 0 and player not in self.finished_players:
            self.finished_players.append(player)

        # Game over when 3 players finish
        done = len(self.finished_players) >= 3 
        
        # Calculate reward (simple placeholder)
        reward = 0
        if len(self.hands[player]) == 0:
            reward = 100 # Bonus for finishing

        # 4. Next Player
        self._advance_turn()

        return self.get_state(), reward, done, {}

    def _advance_turn(self):
        """Move to the next active player."""
        if self.pass_count >= 3:
            # New round, clear last play
            self.last_play = None
            self.pass_count = 0
        
        next_p = (self.current_player + 1) % 4
        # Skip finished players
        while next_p in self.finished_players and len(self.finished_players) < 4:
             next_p = (next_p + 1) % 4
        self.current_player = next_p

    def _get_card_val_map(self) -> Dict[str, int]:
        card_val = {
            "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "T": 10, "J": 11,
            "Q": 12, "K": 13, "A": 14, "B": 16, "R": 17
        }
        card_val[self.rank] = 15
        return card_val

    def _get_action_type(self, action: List[str]) -> str:
        """Identify the type of the action using HandCombiner."""
        if not action:
            return "PASS"
            
        card_val = self._get_card_val_map()
        # combine_handcards returns all possible combinations.
        sorted_cards, bomb_info = self.combiner.combine_handcards(action, self.rank, card_val)
        
        # Check counts to determine type
        # Note: HandCombiner in src/game_logic only detects Single, Pair, Trips, Bomb (basic).
        # It does NOT detect Straights yet. We need to extend this later.
        
        if len(sorted_cards["Bomb"]) == 1 and len(sorted_cards["Bomb"][0]) == len(action):
            return "Bomb"
            
        if len(sorted_cards["Trips"]) == len(action) and len(action) == 3:
            return "Trips"
            
        if len(sorted_cards["Pair"]) == len(action) and len(action) == 2:
            return "Pair"
            
        if len(sorted_cards["Single"]) == len(action) and len(action) == 1:
            return "Single"
            
        return "Unknown"

    def _is_legal(self, player: int, action: List[str]) -> bool:
        """Check if the action is legal."""
        # 1. Check if player has these cards
        hand = self.hands[player]
        # Create a frequency map to handle duplicates correctly
        hand_counts = {}
        for card in hand:
            hand_counts[card] = hand_counts.get(card, 0) + 1
            
        for card in action:
            if hand_counts.get(card, 0) > 0:
                hand_counts[card] -= 1
            else:
                return False
        
        # 2. Check if it beats the last play
        if not action:
            # Can't pass if you are the leader (last_play is None or last_play was cleared)
            return self.last_play is not None
        
        action_type = self._get_action_type(action)
        if action_type == "Unknown":
            return False

        if self.last_play is None:
            return True # Any valid combination is allowed
        
        last_player, last_type, last_cards = self.last_play
        
        # Logic for beating cards
        # 1. Bomb/StraightFlush beats everything else
        is_bomb = action_type in ["Bomb", "StraightFlush"]
        last_is_bomb = last_type in ["Bomb", "StraightFlush"]
        
        if is_bomb and not last_is_bomb:
            return True
        if not is_bomb and last_is_bomb:
            return False
            
        # 2. Must be same type and greater value
        if action_type != last_type:
            return False
            
        if len(action) != len(last_cards):
            return False
            
        # Compare values
        return self._compare_values(action, last_cards, action_type)

    def _compare_values(self, action: List[str], last: List[str], ctype: str) -> bool:
        """Compare values of two actions of same type."""
        card_val = self._get_card_val_map()
        
        # Get representative value for the combination
        def get_repr_val(cards):
            # Simplified: Max value in the set
            return max(self._card_sort_key(c) for c in cards)
            
        return get_repr_val(action) > get_repr_val(last)

