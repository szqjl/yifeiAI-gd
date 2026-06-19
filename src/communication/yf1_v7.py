# -*- coding: utf-8 -*-
"""
yf1_v7 - YiFei AI V7 Client (Player 0)
Ultimate Win Rate Oriented Version
终极胜率导向版本：使用终极胜率导向训练模型
"""
import asyncio
import json
import sys
import logging
from pathlib import Path
import time

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from v.nn import UltimateWinRateEngineV7
from communication.v7_game_recorder import (
    GameRecorder,
    normalize_cards_to_string_list,
    normalize_action_list,
    ensure_my_pos_int,
    unwrap_platform_payload,
    process_platform_game_end_notify,
    normalize_act_message_fields,
    decision_context_from_act,
    is_ws_debug_enabled,
)
from communication.websocket_manager import WebSocketManager
from config_loader import get_config
from game_logic.guandan_constants import CARDS_PER_PLAYER

# Configure logging
log_dir = Path(__file__).parent.parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

from datetime import datetime
log_filename = log_dir / f"yf1_v7_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Connection delay to ensure proper position assignment
DELAY_BEFORE_CONNECT = 2  # seconds — 批跑 restart_manager 已按序间隔启动


class YF1_V7_Client:
    """
    YiFei AI V7 Client - Player 0
    Ultimate Win Rate Oriented Version
    """
    
    def __init__(self, player_id=0, use_local_websocket=True):
        self.player_id = player_id
        self.user_info = "yf1_v7"
        self.logger = logging.getLogger(f"yf1_v7")
        
        # Initialize WebSocket manager
        self.ws_manager = WebSocketManager(self.user_info, use_local=use_local_websocket)
        self.websocket = None
        
        # Initialize Ultimate Win Rate Decision Engine V7
        self.logger.info("🎯 Initializing Ultimate Win Rate Engine V7")
        self.decision_engine = UltimateWinRateEngineV7(player_id, use_grouping_engine=True)
        
        self.hand_cards = []
        
        # Statistics
        self.decision_count = 0
        self.game_count = 0
        
        # Initialize game recorder
        self.game_recorder = GameRecorder(player_id, "yf1_v7")

        self.max_decision_time = float(
            get_config().get("decision.max_decision_time", 0.8)
        )
        self.ws_debug = is_ws_debug_enabled()
        
        self.logger.info(f"✓ yf1_v7 initialized (Player {player_id})")
        self.logger.info(f"  - Ultimate Win Rate Engine V7: Loaded")
    
    async def connect(self):
        """Connect to game server"""
        try:
            self.logger.info(f"[yf1_v7] 等待连接延迟 {DELAY_BEFORE_CONNECT} 秒，确保第一个位置...")
            time.sleep(DELAY_BEFORE_CONNECT)
            self.logger.info(f"[yf1_v7] 开始连接 ws://127.0.0.1:23456/game/yf1_v7")
            
            connected = await self.ws_manager.connect()
            if not connected:
                self.logger.error("Failed to connect to server")
                return
            
            self.websocket = self.ws_manager.websocket
            
            print(f"[yf1_v7] 连接成功！期望位置：{self.player_id}号位")
            self.logger.info(f"✓ Connected to server. Expected position: {self.player_id}")
            
            self.ws_manager.set_message_handler(self.process_message)
            await self.ws_manager.handle_messages()
            
        except Exception as e:
            self.logger.error(f"✗ Connection error: {e}", exc_info=True)
    
    async def process_message(self, data: dict):
        """Process a message from the server"""
        t_msg = time.perf_counter()
        message_type = data.get("type", "")
        
        if self.ws_debug and message_type in ("notify", "act"):
            print(f"\n[服务器消息调试] 收到 {message_type} 消息:")
            print(f"完整消息: {json.dumps(data, indent=2, ensure_ascii=False)[:1500]}...")
        
        if message_type == "act":
            t_act_start = time.perf_counter()
            await self.handle_action_request(data)
            t_act_end = time.perf_counter()
            if t_act_end - t_act_start > 0.5:
                self.logger.warning("[perf] act handler 耗时 %.3fs", t_act_end - t_act_start)
            # 记录整体消息处理耗时
            if t_act_end - t_msg > 1.0:
                self.logger.warning("[perf] 消息处理总耗时 %.3fs type=%s", t_act_end - t_msg, message_type)
        elif message_type == "notify":
            self.handle_notification(data)
    
    def handle_notification(self, data: dict):
        """Handle notification from server"""
        try:
            notification_data = unwrap_platform_payload(data)
            stage = notification_data.get("stage", "")
            notify_type = notification_data.get("notifyType", "")
            key = notify_type or stage

            if key in ("gameStart", "beginning"):
                self.handle_game_start(notification_data)
            elif key in ("gameEnd", "gameOver", "gameResult", "episodeOver"):
                self.handle_game_end(notification_data)
            elif key == "tribute":
                self.game_recorder.record_tribute_notify(notification_data)
            elif key == "back":
                self.game_recorder.record_back_notify(notification_data)
            elif key == "anti-tribute":
                self.logger.info(
                    "抗贡: antiNums=%s antiPos=%s",
                    notification_data.get("antiNums"),
                    notification_data.get("antiPos"),
                )
            elif key == "act" or (stage == "play" and not notify_type):
                self._handle_act_notification(notification_data)
            elif "handCards" in notification_data and not self.game_recorder.current_game:
                self.logger.info("检测到 handCards 且无 current_game，按游戏开始处理")
                self.handle_game_start(notification_data)

            if "handCards" in notification_data:
                self.hand_cards = normalize_cards_to_string_list(notification_data["handCards"])

        except Exception as e:
            self.logger.error(f"✗ Notification handling error: {e}", exc_info=True)
    
    def _handle_act_notification(self, data: dict):
        """出牌 notify → actions（契约对齐 M3 yf1_m3._handle_act_notification）。"""
        hand_cards = data.get("handCards", [])
        if hand_cards:
            valid_cards = normalize_cards_to_string_list(hand_cards)
            if len(valid_cards) <= CARDS_PER_PLAYER:
                self.hand_cards = valid_cards
        self.game_recorder.record_play_notify(data)

    def handle_game_start(self, data: dict):
        """Handle game start notification"""
        try:
            self.game_count += 1
            self.hand_cards = normalize_cards_to_string_list(data.get("handCards", []))
            my_pos = ensure_my_pos_int(data, self.player_id)
            if my_pos != self.player_id:
                self.logger.info(f"Position updated: {self.player_id} -> {my_pos} (server myPos)")
                self.player_id = my_pos
            self.logger.info(
                "[座位排查] 来源=yf1_v7.handle_game_start, 原始myPos=%s, 原始playerPosition=%s, 同步后player_id=%s",
                data.get("myPos"), data.get("playerPosition"), self.player_id
            )

            self.game_recorder.record_game_start(data)
            self.logger.info(f"🎮 游戏开始 #{self.game_count}: 手牌数={len(self.hand_cards)}, 座位={self.player_id}")
            
        except Exception as e:
            self.logger.error(f"✗ Game start handling error: {e}", exc_info=True)
    
    def handle_game_end(self, data: dict):
        """Handle game end notification (episodeOver / gameResult / gameOver)"""
        try:
            process_platform_game_end_notify(
                data,
                self.game_recorder,
                self.logger,
                self.user_info,
                self.decision_count,
                self.game_count,
            )

            stats = self.decision_engine.get_statistics()
            self.logger.info(f"🏁 游戏结束 #{self.game_count}")
            self.logger.info(f"  - 总决策次数: {stats['total_decisions']}")
            self.logger.info(f"  - 模型决策: {stats['model_decisions']}")
            self.logger.info(f"  - 规则回退: {stats['fallback_decisions']}")
            self.logger.info(f"  - 模型使用率: {stats['model_usage_rate']:.1%}")

        except Exception as e:
            self.logger.error(f"✗ Game end handling error: {e}", exc_info=True)
    
    async def handle_action_request(self, data: dict):
        """Handle action request from server"""
        self.decision_count += 1

        action_data = unwrap_platform_payload(data)
        
        # Check stage
        stage = action_data.get("stage", "")
        if stage == "tribute":
            await self._handle_tribute_action(action_data)
            return
        elif stage == "back":
            await self._handle_back_action(action_data)
            return
        
        # Normal play stage
        self_rank = action_data.get("selfRank", "?")
        oppo_rank = action_data.get("oppoRank", "?")
        cur_rank = action_data.get("curRank", "?")
        
        if self_rank != "?" or oppo_rank != "?" or cur_rank != "?":
            print(f"我方等级：{self_rank}， 对方等级：{oppo_rank}， 当前等级{cur_rank}")
        
        action_list = action_data.get("actionList", [])
        
        if not action_list:
            self.logger.warning(
                "Empty actionList stage=%s myPos=%s curPos=%s — 回退 actIndex=0 避免平台超时",
                stage,
                action_data.get("myPos"),
                action_data.get("curPos"),
            )
            await self.send_action(0)
            return
        
        try:
            my_pos = ensure_my_pos_int(action_data, self.player_id)
            if my_pos != self.player_id:
                self.logger.info(f"Position updated: {self.player_id} -> {my_pos} (from act myPos)")
                self.player_id = my_pos
            action_data["myPos"] = self.player_id
            self.logger.info(
                "[座位排查] 来源=yf1_v7.handle_action_request, 原始myPos=%s, 原始playerPosition=%s, 同步后player_id=%s",
                action_data.get("myPos"), action_data.get("playerPosition"), self.player_id
            )
            normalize_act_message_fields(action_data)
            t0 = time.perf_counter()
            try:
                act_index = await asyncio.wait_for(
                    asyncio.to_thread(self.decision_engine.decide, action_data),
                    timeout=self.max_decision_time,
                )
            except asyncio.TimeoutError:
                elapsed = time.perf_counter() - t0
                self.logger.warning(
                    "决策超时 %.2fs (limit=%.2fs)，回退 actIndex=0",
                    elapsed,
                    self.max_decision_time,
                )
                act_index = 0
            else:
                elapsed = time.perf_counter() - t0
                if elapsed > 1.0:
                    self.logger.warning("决策偏慢 %.2fs myPos=%s actionList=%s", elapsed, my_pos, len(action_list))
            print(f"[yf1_v7] 选择动作: {act_index}")
            self.logger.info(f"选择动作: {act_index}")

            selected_action = action_list[act_index] if act_index < len(action_list) else []
            ctx = decision_context_from_act(action_data, self.player_id, version="v7")
            ctx["engine"] = "ultimate_win_rate"
            self.game_recorder.record_decision(act_index, selected_action, context=ctx)
            
            # Validate action index
            if not self.validate_action(act_index, action_list):
                self.logger.error(f"Invalid action index: {act_index}, using 0")
                act_index = 0
            
            await self.send_action(act_index)
            
        except Exception as e:
            self.logger.error(f"✗ Decision error: {e}", exc_info=True)
            await self.send_action(0)
    
    async def _handle_tribute_action(self, data: dict):
        """Handle tribute action - 进贡阶段需要发送动作响应"""
        self_rank = data.get("selfRank", "?")
        oppo_rank = data.get("oppoRank", "?")
        cur_rank = data.get("curRank", "?")
        print(f"[进贡] 我方等级：{self_rank}， 对方等级：{oppo_rank}， 当前等级{cur_rank}")
        
        action_list = data.get("actionList") or []
        if not isinstance(action_list, list) or not action_list:
            self.logger.warning("[进贡] actionList 为空或格式异常: %s", action_list)
            await self.send_action(0)
            return
        act_index = 0
        selected = action_list[act_index]
        print(f"[进贡] 轮到自己进贡，选择: {selected}")
        # GUA-067: 送出进贡 → 从 initial_hand 移除
        self.game_recorder.adjust_initial_hand_for_tribute_back(selected, "remove")
        self.game_recorder.record_decision(
            act_index,
            selected,
            context=decision_context_from_act(data, self.player_id, version="v7"),
        )
        await self.send_action(act_index)
    
    async def _handle_back_action(self, data: dict):
        """Handle back action - 还贡阶段需要发送动作响应"""
        self_rank = data.get("selfRank", "?")
        oppo_rank = data.get("oppoRank", "?")
        cur_rank = data.get("curRank", "?")
        print(f"[还贡] 我方等级：{self_rank}， 对方等级：{oppo_rank}， 当前等级{cur_rank}")
        
        action_list = data.get("actionList") or []
        if not isinstance(action_list, list) or not action_list:
            self.logger.warning("[还贡] actionList 为空或格式异常: %s", action_list)
            await self.send_action(0)
            return
        act_index = 0
        selected = action_list[act_index]
        print(f"[还贡] 轮到自己还贡，选择: {selected}")
        # GUA-067: 送出还牌 → 从 initial_hand 移除
        self.game_recorder.adjust_initial_hand_for_tribute_back(selected, "remove")
        self.game_recorder.record_decision(
            act_index,
            selected,
            context=decision_context_from_act(data, self.player_id, version="v7"),
        )
        await self.send_action(act_index)
    
    def validate_action(self, action_index: int, action_list: list) -> bool:
        """Validate action index"""
        return 0 <= action_index < len(action_list)
    
    async def send_action(self, action_index: int):
        """Send action to server（平台标准格式：仅 actIndex）"""
        try:
            message = {"actIndex": action_index}
            await self.ws_manager.send_json(message)
            self.logger.info(f"发送动作: actIndex={action_index}")

        except Exception as e:
            self.logger.error(f"✗ Send action error: {e}", exc_info=True)


async def main():
    """Main function"""
    client = YF1_V7_Client()
    await client.connect()


if __name__ == "__main__":
    asyncio.run(main())