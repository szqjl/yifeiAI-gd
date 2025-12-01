import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.decision.rl_decision_engine import RLDecisionEngine

def test_integration():
    print("Testing RL Decision Engine Integration...")
    
    # 1. Init Engine
    # Ensure model exists or handle missing model gracefully (Engine does this)
    engine = RLDecisionEngine("models/ppo_model_v1.pth")
    
    # 2. Mock State
    mock_state = {
        'hand': ['H2', 'S3', 'D4', 'C5', 'H6'],
        'table': [],
        'history': []
    }
    
    # 3. Get Action
    action = engine.get_action(mock_state)
    print(f"Input Hand: {mock_state['hand']}")
    print(f"Model Output Action: {action}")
    
    # 4. Verify Output Type
    if isinstance(action, list) and all(isinstance(c, str) for c in action):
        print("Integration Test Passed: Output is a list of strings.")
    else:
        print("Integration Test Failed: Invalid output format.")

if __name__ == "__main__":
    test_integration()
