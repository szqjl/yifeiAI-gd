import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from rl_env.game_engine import GameEngine
from rl_env.guandan_env import GuandanEnv

def test_engine():
    print("Testing GameEngine...")
    engine = GameEngine()
    state = engine.reset()
    print("Initial State Keys:", state.keys())
    print("Hand Sizes:", {p: len(h) for p, h in state['hands'].items()})
    
    # Test Pass
    try:
        # Player 0 starts. Let's try to pass (should fail as leader)
        engine.step([])
    except ValueError as e:
        print(f"Caught expected error for passing as leader: {e}")

    print("GameEngine Test Passed!")

def test_gym_env():
    print("\nTesting GuandanEnv...")
    env = GuandanEnv()
    obs, info = env.reset()
    print("Observation Shape:", obs.shape)
    
    # Random Action
    action = env.action_space.sample()
    obs, reward, done, truncated, info = env.step(action)
    print(f"Step Result: Reward={reward}, Done={done}")
    
    print("GuandanEnv Test Passed!")

if __name__ == "__main__":
    test_engine()
    test_gym_env()
