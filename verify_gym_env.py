import sys
import os
import numpy as np
# Add project root to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.rl_env.guandan_env import GuandanEnv

def test_gym_env():
    print("Testing GuandanEnv...")
    try:
        env = GuandanEnv()
    except ImportError as e:
        print(f"ImportError: {e}")
        print("Please install gymnasium: pip install gymnasium")
        return

    # Test Reset
    obs, info = env.reset()
    print(f"Reset Obs Shape: {obs.shape}")
    assert obs.shape == (115,)
    
    # Test Step (Random Action)
    action = env.action_space.sample()
    # action is array of 54 integers
    print(f"Sample Action: {action}")
    
    obs, reward, done, truncated, info = env.step(action)
    print(f"Step Reward: {reward}")
    print(f"Step Done: {done}")
    print(f"Step Info: {info}")
    
    assert obs.shape == (115,)
    
    print("GuandanEnv Tests Passed!")

if __name__ == "__main__":
    test_gym_env()
