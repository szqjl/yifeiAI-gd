# -*- coding: utf-8 -*-
"""
yf1_v5 - YiFei AI V5 Client (Player 0)
Enhanced version with improved RL integration and knowledge base
升级版本：增强的RL集成和知识库应用
"""
import asyncio
import json
import sys
import logging
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent)) # Add project root

from decision.hybrid_decision_engine_v4 import HybridDecisionEngineV4
from decision.rl_decision_engine import RLDecisionEngine
from communication.game_recorder import GameRecorder
from communication.websocket_manager import WebSocketManager

# Configure logging
import os
from datetime import datetime

# 创建日志目录
log_dir = Path(__file__).parent.parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

# 日志文件名：yf1_v5_YYYYMMDD_HHMMSS.log
log_filename = log_dir / f"yf1_v5_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# 配置日志：同时输出到控制台和文件
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),  # 文件输出
        logging.StreamHandler()  # 控制台输出
    ]
)


class YF1_V5_Client:
    """
    YiFei AI V5 Client - Player 0
    Enhanced version with:
    - Improved RL integration (智能RL决策)
    - Enhanced knowledge base application (增强知识库应用)
    - Better decision fusion (更好的决策融合)
    """
    
    def __init__(self, player_id=0, use_local_websocket=True):
        self.player_id = player_id
        self.user_info = "yf1_v5"
        self.logger = logging.getLogger(f"yf1_v5")
        
        # 初始化 WebSocket 管理器（从配置文件读取设置）
        self.ws_manager = WebSocketManager(self.user_info, use_local=use_local_websocket)
        self.websocket = None  # 保持向后兼容
        
        # Initialize HybridDecisionEngineV4 (基础决策引擎)
        config = {
            "enable_lalala": True,
            "enable_fallback": True,
            "log_level": "INFO",
            "performance_threshold": 1.0
        }
        self.decision_engine = HybridDecisionEngineV4(player_id, config)
        
        # Initialize RL Engine (V5增强：更智能的RL集成)
        try:
            self.rl_engine = RLDecisionEngine()
            self.rl_available = True
            self.logger.info("✓ RL Engine initialized")
        except Exception as e:
            self.logger.warning(f"⚠ RL Engine not available: {e}")
            self.rl_engine = None
            self.rl_available = False
        
        # V5特性：智能决策融合
        self.use_hybrid_decision = True  # 使用混合决策（RL + Knowledge + Rule-based）
        self.rl_weight = 0.3  # RL决策权重
        self.knowledge_weight = 0.5  # 知识库权重
        self.rule_weight = 0.2  # 规则引擎权重
        
        self.hand_cards = [] # Track current hand
        
        # Statistics
        self.decision_count = 0
        self.game_count = 0
        self.rl_decision_count = 0
        self.knowledge_decision_count = 0
        
        # Initialize game recorder
        self.game_recorder = GameRecorder(player_id, "yf1_v5")
        
        self.logger.info(f"✓ yf1_v5 initialized (Player {player_id})")
        self.logger.info(f"  - RL Engine: {'Available' if self.rl_available else 'Not Available'}")
        self.logger.info(f"  - Hybrid Decision: {self.use_hybrid_decision}")
    
    async def connect(self):
        """Connect to game server using configured WebSocket manager"""
        try:
            # 使用 WebSocket 管理器连接
            connected = await self.ws_manager.connect()
            if not connected:
                self.logger.error("Failed to connect to server")
                return
            
            # 设置 websocket 引用以保持向后兼容
            self.websocket = self.ws_manager.websocket
            
            # 设置消息处理回调
            self.ws_manager.set_message_handler(self.process_message)
            
            # 开始处理消息
            await self.ws_manager.handle_messages()
        except Exception as e:
            self.logger.error(f"✗ Connection error: {e}", exc_info=True)
    
    async def handle_messages(self):
        """Handle incoming messages from server (deprecated, use ws_manager.handle_messages)"""
        # 此方法已被 ws_manager.handle_messages 替代
        # 保留此方法以保持向后兼容
        await self.ws_manager.handle_messages(self.process_message)
    
    async def process_message(self, data: dict):
        """Process a message from the server"""
        message_type = data.get("type", "")
        
        if message_type == "act":
            await self.handle_action_request(data)
        
        elif message_type == "notify":
            self.handle_notification(data)
    
    async def handle_action_request(self, data: dict):
        """Handle action request from server (V5增强决策)"""
        self.decision_count += 1
        action_list = data.get("actionList", [])
        
        if not action_list:
            self.logger.warning("Empty action list, sending 0")
            await self.send_action(0)
            return
        
        try:
            # V5增强：智能混合决策
            if self.use_hybrid_decision:
                act_index = self._hybrid_decision(data, action_list)
            else:
                # 回退到V4决策
                act_index = self.decision_engine.decide(data)
            
            # Get decision details for recording
            decision_context = {
                "myPos": data.get("myPos", self.player_id),
                "curPos": data.get("curPos", -1),
                "greaterPos": data.get("greaterPos", -1),
                "actionList_size": len(action_list),
                "version": "v5",
                "decision_type": "hybrid" if self.use_hybrid_decision else "v4_fallback"
            }
            
            # Record decision
            selected_action = action_list[act_index] if act_index < len(action_list) else []
            self.game_recorder.record_decision(act_index, selected_action, context=decision_context)
            
            # Validate action index
            if not self.validate_action(act_index, action_list):
                self.logger.error(f"Invalid action index: {act_index}, using 0")
                act_index = 0
            
            await self.send_action(act_index)
        
        except Exception as e:
            self.logger.error(f"✗ Decision error: {e}", exc_info=True)
            # Emergency fallback: send PASS (0)
            await self.send_action(0)
    
    def _hybrid_decision(self, data: dict, action_list: list) -> int:
        """
        V5增强：智能混合决策
        
        融合多种决策源：
        1. RL决策（如果可用）
        2. 知识库增强决策（HybridDecisionEngineV4）
        3. 规则引擎决策
        
        Args:
            data: 游戏状态消息
            action_list: 可用动作列表
            
        Returns:
            最优动作索引
        """
        candidates = []
        
        # 1. 获取基础决策引擎的候选（包含知识库增强）
        try:
            # 使用V4引擎生成候选（已经包含知识库增强）
            base_candidates = self.decision_engine._generate_candidates(data)
            if base_candidates:
                # 增强候选（知识库已应用）
                enhanced_candidates = self.decision_engine._enhance_candidates(base_candidates, data)
                for idx, score, layer in enhanced_candidates:
                    # 应用知识库权重
                    weighted_score = score * self.knowledge_weight
                    candidates.append((idx, weighted_score, "Knowledge"))
                    self.knowledge_decision_count += 1
        except Exception as e:
            self.logger.warning(f"Base decision engine failed: {e}")
        
        # 2. 获取RL决策（如果可用）
        if self.rl_available and self.rl_engine:
            try:
                # 注入手牌信息
                data_with_hand = data.copy()
                data_with_hand['handCards'] = self.hand_cards
                
                rl_action = self.rl_engine.decide(data_with_hand)
                if rl_action is not None and 0 <= rl_action < len(action_list):
                    # RL决策评分（使用权重）
                    rl_score = 100.0 * self.rl_weight  # 基础RL评分
                    candidates.append((rl_action, rl_score, "RL"))
                    self.rl_decision_count += 1
                    self.logger.debug(f"RL decision: action={rl_action}, score={rl_score:.1f}")
            except Exception as e:
                self.logger.warning(f"RL decision failed: {e}")
        
        # 3. 如果没有候选，使用V4引擎的decide方法
        if not candidates:
            self.logger.warning("No candidates from hybrid decision, using V4 fallback")
            return self.decision_engine.decide(data)
        
        # 4. 选择最优动作（按加权评分排序）
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_action, best_score, best_source = candidates[0]
        
        self.logger.debug(
            f"Hybrid decision: action={best_action}, score={best_score:.1f}, "
            f"source={best_source}, candidates={len(candidates)}"
        )
        
        return best_action
    
    def handle_notification(self, data: dict):
        """Handle notification from server"""
        stage = data.get("stage", "")
        
        if stage == "beginning":
            # 获取初始手牌信息
            hand_cards = data.get("handCards", [])
            self.hand_cards = hand_cards # Store for RL engine
            my_pos = data.get("myPos", self.player_id)
            
            # 更新实际位置（服务器分配的）
            if my_pos != self.player_id:
                self.logger.info(f"Position updated: {self.player_id} -> {my_pos}")
                self.player_id = my_pos
            
            # 打印手牌信息（与lalala客户端格式一致）
            print(f"游戏开始, 我是{my_pos}号位，手牌：{hand_cards}")
            self.logger.info(f"游戏开始, 我是{my_pos}号位，手牌：{hand_cards}")
            
            # 打印等级信息（用于调试）
            self_rank = data.get("selfRank", "?")
            oppo_rank = data.get("oppoRank", "?")
            cur_rank = data.get("curRank", "?")
            print(f"我方等级：{self_rank}， 对方等级：{oppo_rank}， 当前等级{cur_rank}")
            
            # 尝试获取所有玩家的手牌信息
            all_players_hands = {}
            all_players_hands[my_pos] = hand_cards  # 自己的手牌
            
            # 从publicInfo中获取其他玩家的剩余牌数（如果有）
            public_info = data.get("publicInfo", [])
            if public_info:
                for i, player_info in enumerate(public_info):
                    if isinstance(player_info, dict) and "rest" in player_info:
                        pass
            
            # 从restCards中获取其他玩家的手牌（如果有）
            rest_cards = data.get("restCards", [])
            if rest_cards:
                for rest_info in rest_cards:
                    if isinstance(rest_info, list) and len(rest_info) >= 2:
                        pos = rest_info[0]
                        if isinstance(pos, str):
                            try:
                                pos = int(pos)
                            except:
                                continue
                        cards = rest_info[1]
                        if cards and isinstance(cards, list) and len(cards) > 0:
                            if isinstance(cards[0], list):
                                normalized_cards = [f"{c[0]}{c[1]}" if isinstance(c, list) and len(c) >= 2 else str(c) for c in cards]
                                cards = normalized_cards
                        if pos != my_pos:
                            all_players_hands[pos] = cards
                            self.logger.info(f"记录{pos}号位手牌: {len(cards)}张")
            
            # 确保my_pos也是整数键
            if isinstance(my_pos, str):
                try:
                    my_pos = int(my_pos)
                except:
                    pass
            if my_pos in all_players_hands and isinstance(my_pos, str):
                all_players_hands[int(my_pos)] = all_players_hands.pop(my_pos)
            elif not isinstance(my_pos, str):
                all_players_hands[my_pos] = hand_cards
            
            if len(all_players_hands) > 1:
                self.logger.info(f"已记录{len(all_players_hands)}个玩家的手牌: {list(all_players_hands.keys())}")
            
            # 开始记录游戏
            game_info = {
                "selfRank": data.get("selfRank"),
                "oppoRank": data.get("oppoRank"),
                "curRank": data.get("curRank")
            }
            self.game_recorder.start_game(hand_cards, my_pos, game_info, all_players_hands)
        
        elif stage == "play":
            # 记录每个玩家的出牌信息（用于回放）
            cur_pos = data.get("curPos", -1)
            cur_action = data.get("curAction", [])
            greater_pos = data.get("greaterPos", -1)
            greater_action = data.get("greaterAction", [])
            
            # 格式化出牌信息
            if cur_action and len(cur_action) > 0 and cur_action[0] != "PASS":
                action_str = f"{cur_pos}号位打出{cur_action}"
                greater_str = f"最大动作为{greater_pos}号位打出的{greater_action}" if greater_action else ""
                self.logger.info(f"{action_str}， {greater_str}")
                
                # Update my hand cards if I played
                if cur_pos == self.player_id:
                    if len(cur_action) >= 3 and isinstance(cur_action[2], list):
                        played_cards = cur_action[2]
                        for card in played_cards:
                            if card in self.hand_cards:
                                self.hand_cards.remove(card)
            
            # 记录到游戏记录器
            context = {
                "publicInfo": data.get("publicInfo", []),
                "selfRank": data.get("selfRank"),
                "oppoRank": data.get("oppoRank"),
                "curRank": data.get("curRank"),
                "restCards": data.get("restCards", [])
            }
            self.game_recorder.record_action(cur_pos, cur_action, greater_pos, greater_action, context)
        
        elif stage == "gameResult":
            self.game_count += 1
            victory_num = data.get("victoryNum", [])
            draws = data.get("draws", [])
            
            result = {
                "victoryNum": victory_num,
                "draws": draws,
                "total_decisions": self.decision_count,
                "game_count": self.game_count,
                "rl_decisions": self.rl_decision_count,
                "knowledge_decisions": self.knowledge_decision_count
            }
            
            self.logger.info("=" * 60)
            self.logger.info("GAME RESULT (V5)")
            self.logger.info("=" * 60)
            self.logger.info(f"Victory counts: {victory_num}")
            self.logger.info(f"Total decisions: {self.decision_count}")
            self.logger.info(f"  - RL decisions: {self.rl_decision_count}")
            self.logger.info(f"  - Knowledge decisions: {self.knowledge_decision_count}")
            self.logger.info(f"Total games played: {self.game_count}")
            
            # Get statistics from decision engine
            stats = self.decision_engine.get_statistics()
            self.logger.info(f"Layer usage statistics:")
            for layer, layer_data in stats["layer_usage"].items():
                success = layer_data["success"]
                failure = layer_data["failure"]
                total = success + failure
                if total > 0:
                    rate = success / total * 100
                    self.logger.info(f"  {layer}: {success}/{total} ({rate:.1f}%)")
            
            self.logger.info("=" * 60)
            
            # 保存游戏记录
            result["layer_stats"] = stats["layer_usage"]
            self.game_recorder.end_game(result)
            
            # 保存战绩到 game_scores.json（用于GUI显示）
            self._save_game_scores(victory_num)
            
            # Reset for next game
            self.decision_count = 0
            self.rl_decision_count = 0
            self.knowledge_decision_count = 0
            self.decision_engine.reset_statistics()
    
    def validate_action(self, act_index: int, action_list: list) -> bool:
        """Validate that action index is in valid range"""
        return 0 <= act_index < len(action_list)
    
    def _save_game_scores(self, victory_num: list):
        """
        保存战绩到 game_scores.json（用于GUI显示）
        
        注意：位置是服务器动态分配的，需要根据实际 myPos 判断队友
        
        Args:
            victory_num: 胜利次数列表 [pos0_wins, pos1_wins, pos2_wins, pos3_wins]
        """
        import json
        from pathlib import Path
        
        score_file = Path("game_scores.json")
        
        # 读取现有战绩
        if score_file.exists():
            try:
                with open(score_file, 'r', encoding='utf-8') as f:
                    scores = json.load(f)
            except:
                scores = {"team_a_wins": 0, "team_b_wins": 0, "total_games": 0, "my_pos": None, "teammate_pos": None}
        else:
            scores = {"team_a_wins": 0, "team_b_wins": 0, "total_games": 0, "my_pos": None, "teammate_pos": None}
        
        # 记录位置信息（用于调试）
        if scores.get("my_pos") is None:
            scores["my_pos"] = self.player_id
            teammate_pos = (self.player_id + 2) % 4
            scores["teammate_pos"] = teammate_pos
            self.logger.info(f"Position info saved: my_pos={self.player_id}, teammate_pos={teammate_pos}")
        
        # 判断获胜队伍
        # 在掼蛋中，0和2是队友，1和3是队友
        # 但实际位置是服务器分配的，所以用 self.player_id 来判断
        if len(victory_num) >= 4:
            my_pos = self.player_id
            teammate_pos = (my_pos + 2) % 4
            opponent1_pos = (my_pos + 1) % 4
            opponent2_pos = (my_pos + 3) % 4
            
            # Team A: yf1_v5 + yf2_v5 (我方)
            team_a_score = victory_num[my_pos] + victory_num[teammate_pos]
            # Team B: 对手
            team_b_score = victory_num[opponent1_pos] + victory_num[opponent2_pos]
            
            # 更新战绩
            if team_a_score > team_b_score:
                scores["team_a_wins"] += 1
                self.logger.info(f"YF Team wins! (pos {my_pos}+{teammate_pos}: {team_a_score} vs pos {opponent1_pos}+{opponent2_pos}: {team_b_score})")
            elif team_b_score > team_a_score:
                scores["team_b_wins"] += 1
                self.logger.info(f"Opponent Team wins! (pos {opponent1_pos}+{opponent2_pos}: {team_b_score} vs pos {my_pos}+{teammate_pos}: {team_a_score})")
            else:
                # 平局，不增加胜场
                self.logger.info(f"Draw! ({team_a_score} vs {team_b_score})")
            
            scores["total_games"] += 1
        
        # 保存到文件
        try:
            with open(score_file, 'w', encoding='utf-8') as f:
                json.dump(scores, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Game scores saved: YF Team {scores['team_a_wins']}/{scores['total_games']}, Opponent Team {scores['team_b_wins']}/{scores['total_games']}")
        except Exception as e:
            self.logger.error(f"Failed to save game scores: {e}")
    
    async def send_action(self, act_index: int):
        """Send action to server using WebSocket manager"""
        response = {"actIndex": act_index}
        await self.ws_manager.send_json(response)
        self.logger.debug(f"Sent action: {act_index}")


async def main():
    """Main entry point"""
    # 设置stdout编码为UTF-8，避免Windows下的编码问题
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    client = YF1_V5_Client(player_id=0)
    await client.connect()


if __name__ == "__main__":
    asyncio.run(main())

