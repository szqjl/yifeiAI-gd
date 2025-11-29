# -*- coding: utf-8 -*-
"""
Test2_V4 - Hybrid Decision Engine V4 Client (Player 2)
Uses HybridDecisionEngineV4 with 4-layer fallback protection
"""
import asyncio
import websockets
import json
import sys
import logging
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent))

from decision.hybrid_decision_engine_v4 import HybridDecisionEngineV4

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)


class Test2V4Client:
    """
    Test2_V4 Client - Player 1
    Uses HybridDecisionEngineV4 for robust decision making
    """
    
    def __init__(self, player_id=2):
        self.player_id = player_id
        self.user_info = "Test2_V4"
        self.websocket = None
        self.logger = logging.getLogger(f"Test2_V4")
        
        # Initialize HybridDecisionEngineV4
        config = {
            "enable_lalala": True,
            "enable_fallback": True,
            "log_level": "INFO",
            "performance_threshold": 1.0
        }
        self.decision_engine = HybridDecisionEngineV4(player_id, config)
        
        # Statistics
        self.decision_count = 0
        self.game_count = 0
        
        self.logger.info(f"✓ Test2_V4 initialized (Player {player_id})")
    
    async def connect(self):
        """Connect to game server"""
        uri = f"ws://127.0.0.1:23456/game/{self.user_info}"
        try:
            self.websocket = await websockets.connect(
                uri,
                ping_timeout=None,  # Disable ping timeout
                close_timeout=10
            )
            self.logger.info(f"✓ Connected to server: {uri}")
            await self.handle_messages()
        except Exception as e:
            self.logger.error(f"✗ Connection error: {e}")
    
    async def handle_messages(self):
        """Handle incoming messages from server"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self.process_message(data)
                
                except json.JSONDecodeError as e:
                    self.logger.error(f"✗ Invalid JSON: {e}")
                except Exception as e:
                    self.logger.error(f"✗ Message processing error: {e}", exc_info=True)
        
        except websockets.ConnectionClosed as e:
            self.logger.info(f"Connection closed: {e}")
        except Exception as e:
            self.logger.error(f"✗ Connection error: {e}", exc_info=True)
        finally:
            self.logger.info("Disconnected from server")
    
    async def process_message(self, data: dict):
        """Process a message from the server"""
        message_type = data.get("type", "")
        
        if message_type == "act":
            await self.handle_action_request(data)
        
        elif message_type == "notify":
            self.handle_notification(data)
    
    async def handle_action_request(self, data: dict):
        """Handle action request from server"""
        self.decision_count += 1
        action_list = data.get("actionList", [])
        
        if not action_list:
            self.logger.warning("Empty action list, sending 0")
            await self.send_action(0)
            return
        
        try:
            # Use HybridDecisionEngineV4 to make decision
            act_index = self.decision_engine.decide(data)
            
            # Validate action index
            if not self.validate_action(act_index, action_list):
                self.logger.error(f"Invalid action index: {act_index}, using 0")
                act_index = 0
            
            await self.send_action(act_index)
        
        except Exception as e:
            self.logger.error(f"✗ Decision error: {e}", exc_info=True)
            # Emergency fallback: send PASS (0)
            await self.send_action(0)
    
    def handle_notification(self, data: dict):
        """Handle notification from server"""
        stage = data.get("stage", "")
        
        if stage == "gameResult":
            self.game_count += 1
            victory_num = data.get("victoryNum", [])
            
            self.logger.info("=" * 60)
            self.logger.info("GAME RESULT")
            self.logger.info("=" * 60)
            self.logger.info(f"Victory counts: {victory_num}")
            self.logger.info(f"Total decisions this game: {self.decision_count}")
            self.logger.info(f"Total games played: {self.game_count}")
            
            # Get statistics from decision engine
            stats = self.decision_engine.get_statistics()
            self.logger.info(f"Layer usage statistics:")
            for layer, data in stats["layer_usage"].items():
                success = data["success"]
                failure = data["failure"]
                total = success + failure
                if total > 0:
                    rate = success / total * 100
                    self.logger.info(f"  {layer}: {success}/{total} ({rate:.1f}%)")
            
            self.logger.info("=" * 60)
            
            # Reset for next game
            self.decision_count = 0
            self.decision_engine.reset()
    
    def validate_action(self, act_index: int, action_list: list) -> bool:
        """Validate that action index is in valid range"""
        return 0 <= act_index < len(action_list)
    
    async def send_action(self, act_index: int):
        """Send action to server"""
        response = json.dumps({"actIndex": act_index})
        await self.websocket.send(response)
        self.logger.debug(f"Sent action: {act_index}")


async def main():
    """Main entry point"""
    client = Test2_V4_Client(player_id=2)
    await client.connect()


if __name__ == "__main__":
    asyncio.run(main())

