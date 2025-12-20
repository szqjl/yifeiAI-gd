import sys
from pathlib import Path

# Add src to path
if str(Path("d:/YiFeiAI-GD/src")) not in sys.path:
    sys.path.insert(0, str(Path("d:/YiFeiAI-GD/src")))

try:
    from communication.modern_client import ModernGuandanClient
    client = ModernGuandanClient("TestUser")
    print("Successfully instantiated ModernGuandanClient")
    print(f"Decision Engine: {client.decision_engine}")
except Exception as e:
    print(f"Failed to instantiate: {e}")
    import traceback
    traceback.print_exc()
