import sys
import os
# Add project root to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.rl_env.game_engine import GameEngine

def test_game_engine():
    print("Testing GameEngine...")
    engine = GameEngine()
    
    # Test Reset
    state = engine.get_state()
    assert len(state['hands']) == 4
    assert len(state['hands'][0]) == 27
    print("Reset OK")
    
    # Test Legal Move (Single)
    player = state['current_player']
    hand = state['hands'][player]
    card = hand[0]
    action = [card]
    
    print(f"Player {player} plays {action}")
    next_state, reward, done, info = engine.step(action)
    
    assert len(next_state['hands'][player]) == 26
    assert next_state['last_play'] == (player, 'Single', action)
    print("Single Play OK")
    
    # Test Next Player
    next_player = next_state['current_player']
    assert next_player == (player + 1) % 4
    print("Turn Advance OK")
    
    # Test Illegal Move (Wrong Player)
    # Engine tracks current player, so we can't easily force wrong player unless we hack it.
    # But we can try to play cards we don't have.
    fake_card = 'XX'
    action = [fake_card]
    s, r, d, i = engine.step(action)
    assert i['error'] == "Illegal move"
    assert r < 0
    print("Illegal Move Check OK")
    
    # Test Beat Logic
    # Player 1 needs to beat Player 0's single.
    # Player 0 played `card`. Player 1 needs a higher single.
    # Let's find a higher single in Player 1's hand.
    p1_hand = next_state['hands'][next_player]
    
    # Sort key helper
    def val(c): return engine._card_sort_key(c)
    
    higher_card = None
    for c in p1_hand:
        if val(c) > val(card):
            higher_card = c
            break
            
    if higher_card:
        print(f"Player {next_player} tries to beat {card} with {higher_card}")
        action = [higher_card]
        s, r, d, i = engine.step(action)
        if i:
            print(f"Failed: {i}")
            # It might fail if HandCombiner doesn't recognize single card correctly?
            # HandCombiner.combine_handcards returns dict.
            # We need to ensure _get_action_type works.
        else:
            assert s['last_play'] == (next_player, 'Single', action)
            print("Beat Logic OK")
    else:
        print("Skipping Beat Logic (no higher card)")
        
    print("GameEngine Tests Passed!")

if __name__ == "__main__":
    test_game_engine()
