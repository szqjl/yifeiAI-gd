# -*- coding: utf-8 -*-
"""
yf2_v8 - YiFei AI V8 Client (Player 2) — OpenGuanDan 新平台适配版
从 yf2_v7.py 复制而来，在新平台上替代 v1006 WebSocket 协议。
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
from communication.v8_game_recorder import (
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
from communication.v8_websocket_manager import WebSocketManager
from communication.new_platform_adapter import OpenGuanDanAdapter
from config_loader import get_config
from game_logic.guandan_constants import CARDS_PER_PLAYER

# Configure logging
log_dir = Path(__file__).parent.parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

from datetime import datetime
log_filename = log_dir / f"yf2_v8_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

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
DELAY_BEFORE_CONNECT = 4  # seconds — 在 client3 之后连入


class YF2_V8_Client:
    """
    YiFei AI V8 Client - Player 2 (OpenGuanDan 新平台)
    Ultimate Win Rate Oriented Version
    """
    
    def __init__(self, player_id=2, use_local_websocket=True,
                 platform: str = "v1006",
                 v8_role: str = None, v8_round_count: int = 1):
        self.player_id = player_id
        self.user_info = "yf2_v8"
        self.logger = logging.getLogger(f"yf2_v8")
        self.platform = platform
        
        self.adapter = None
        if platform == "openguandan":
            self.adapter = OpenGuanDanAdapter(user_id=self.user_info, seat_num=player_id)
        
        self.ws_manager = WebSocketManager(
            self.user_info, use_local=use_local_websocket,
            platform=platform,
            v8_role=v8_role, v8_round_count=v8_round_count,
        )
        if self.adapter:
            self.ws_manager.set_adapter(self.adapter)
        self.websocket = None
        
        # Initialize Ultimate Win Rate Decision Engine V7
        self.logger.info("🎯 Initializing Ultimate Win Rate Engine V7")
        self.decision_engine = UltimateWinRateEngineV7(player_id, use_grouping_engine=True)
        
        self.hand_cards = []
        
        # Statistics
        self.decision_count = 0
        self.game_count = 0
        
        # Initialize game recorder
        self.game_recorder = GameRecorder(player_id, "yf2_v8")

        # V8: actionList/tribute 缓存
        self.last_action_list = []
        self.last_stage = ""
        self.last_tribute_pos = None
        self.last_tribute_card = None

        self._episode_tribute_result = None
        self._episode_anti_pos = None
        self._episode_back_result = None

        self.max_decision_time = float(
            get_config().get("decision.max_decision_time", 0.8)
        )
        self.ws_debug = is_ws_debug_enabled()
        
        self.logger.info(f"✓ yf2_v8 initialized (Player {player_id}, platform={platform})")
        self.logger.info(f"  - Ultimate Win Rate Engine V7: Loaded")

    def _reset_episode_tribute_state(self) -> None:
        self._episode_tribute_result = None
        self._episode_anti_pos = None
        self._episode_back_result = None
    
    async def connect(self):
        """Connect to game server"""
        try:
            self.logger.info(f"[yf2_v8] 等待连接延迟 {DELAY_BEFORE_CONNECT} 秒，确保第三个位置...")
            time.sleep(DELAY_BEFORE_CONNECT)
            port = "8181" if self.platform == "openguandan" else "23456"
            self.logger.info(f"[yf2_v8] 开始连接 ws://127.0.0.1:{port}/game/yf2_v8")
            
            connected = await self.ws_manager.connect()
            if not connected:
                self.logger.error("Failed to connect to server")
                return
            
            self.websocket = self.ws_manager.websocket
            
            print(f"[yf2_v8] 连接成功！期望位置：{self.player_id}号位")
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
                self._reset_episode_tribute_state()
                self.handle_game_start(notification_data)
            elif key in ("gameEnd", "gameOver", "gameResult", "episodeOver"):
                if key == "episodeOver":
                    self._reset_episode_tribute_state()
                self.handle_game_end(notification_data)
            elif key == "tribute":
                self._episode_tribute_result = notification_data.get("result")
                self.game_recorder.record_tribute_notify(notification_data)
            elif key == "back":
                self._episode_back_result = notification_data.get("result")
                self.game_recorder.record_back_notify(notification_data)
            elif key == "anti-tribute":
                self._episode_anti_pos = notification_data.get("antiPos")
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
        """出牌 notify → actions（契约对齐 M3 yf2_m3._handle_act_notification）。"""
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
                "[座位排查] 来源=yf2_v8.handle_game_start, 原始myPos=%s, 原始playerPosition=%s, 同步后player_id=%s",
                data.get("myPos"), data.get("playerPosition"), self.player_id
            )

            self.game_recorder.record_game_start(data)
            # 清理引擎跨局残留状态（R11记忆/R15相克锁/MemoryTracker等）
            trace_game_id = None
            try:
                trace_game_id = (self.game_recorder.current_game or {}).get("game_id")
            except Exception:
                trace_game_id = None
            self.decision_engine.on_game_start(self.player_id, game_id=trace_game_id)
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
            self.logger.info(f"  - 启发式决策: {stats.get('heuristic_decisions', 0)}")
            self.logger.info(f"  - 模型决策: {stats['model_decisions']}")
            self.logger.info(f"  - 规则回退: {stats['fallback_decisions']}")
            self.logger.info(f"  - 模型使用率: {stats['model_usage_rate']:.1%}")
            # GUA-072: 对手无压制牌信念触发统计
            entered = stats.get('no_suppress_opp_control_entered', 0)
            blocked = stats.get('no_suppress_belief_says_can', 0)
            triggered = stats.get('no_suppress_total', 0)
            diag = stats.get('no_suppress_diag', {})
            self.logger.info(
                f"  - GUA-072 进入={entered} 阻={blocked} 触发={triggered}"
                f" (炸={stats.get('no_suppress_bomb_used', 0)} 大牌={stats.get('no_suppress_max_card_used', 0)})"
            )
            self.logger.info(
                f"  - GUA-072 注入诊断: 无tracker={diag.get('tracker_absent',0)}"
                f" 非对手控牌={diag.get('not_opp_control',0)}"
                f" 缺Action={diag.get('no_action',0)}"
                f" True={diag.get('belief_true',0)}"
                f" False={diag.get('belief_false',0)}"
                f" 异常={diag.get('exception',0)}"
            )
            # GUA-075: 推荐路径统计
            self.logger.info(
                f"  - GUA-075 推荐: 尝试={stats.get('recommend_count',0)}"
                f" 命中={stats.get('recommend_hit_count',0)}"
                f" 通过={stats.get('recommend_valid_count',0)}"
                f" 覆盖率={stats.get('recommend_rate',0):.1%}"
                f" 命中率={stats.get('recommend_hit_rate',0):.1%}"
                f" 通过率={stats.get('recommend_valid_rate',0):.1%}"
            )
            self.logger.info(
                f"  - GUA-075 匹配失败分类: type不匹配={stats.get('match_fail_type_mismatch',0)}"
                f" rank不匹配={stats.get('match_fail_rank_mismatch',0)}"
                f" cards不匹配={stats.get('match_fail_cards_mismatch',0)}"
            )
            trace_fp = self.decision_engine.flush_decision_trace()
            if trace_fp:
                self.logger.info("  - GUA-098 trace落盘: %s", trace_fp)

        except Exception as e:
            self.logger.error(f"✗ Game end handling error: {e}", exc_info=True)
    
    async def handle_action_request(self, data: dict):
        """Handle action request from server"""
        self.decision_count += 1

        action_data = unwrap_platform_payload(data)
        
        # V8: 缓存 actionList 和 stage
        action_list = action_data.get("actionList", [])
        self.last_action_list = action_list
        self.last_stage = action_data.get("stage", "")
        
        # V8: 还贡阶段缓存 tributePos/tribute
        if self.last_stage == "back":
            self.last_tribute_pos = action_data.get("tributePos")
            self.last_tribute_card = action_data.get("tribute")
        
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
        
        # 使用已缓存的 action_list（见上方 last_action_list）
        
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
            action_data["tributeResult"] = self._episode_tribute_result
            action_data["antiPos"] = self._episode_anti_pos
            action_data["backResult"] = self._episode_back_result
            self.logger.info(
                "[座位排查] 来源=yf2_v8.handle_action_request, 原始myPos=%s, 原始playerPosition=%s, 同步后player_id=%s",
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
                self.decision_engine._last_decision_layer = "决策超时"
                self.decision_engine._last_decision_score = None
                self.decision_engine._last_decision_candidates = len(action_list)
                act_index = 0
            else:
                elapsed = time.perf_counter() - t0
                if elapsed > 1.0:
                    self.logger.warning("决策偏慢 %.2fs myPos=%s actionList=%s", elapsed, my_pos, len(action_list))
            print(f"[yf2_v8] 选择动作: {act_index}")
            self.logger.info(f"选择动作: {act_index}")

            selected_action = action_list[act_index] if act_index < len(action_list) else []
            ctx = decision_context_from_act(action_data, self.player_id, version="v7")
            ctx["engine"] = "ultimate_win_rate"
            # GUA-075: 将 card_mask + role + group_type_map 写入 context 供诊断
            try:
                cm = self.decision_engine._card_mask
                if cm:
                    ctx["card_mask"] = {k: list(v) for k, v in cm.items()}
                    ctx["role"] = self.decision_engine._current_role
                    ctx["group_type_map"] = {str(k): v for k, v in (self.decision_engine._group_type_map or {}).items()}
            except Exception:
                pass
            # GUA-075 记录增强: 从引擎读取管线追踪信息
            _layer = self.decision_engine._last_decision_layer
            _score = self.decision_engine._last_decision_score
            _candidates_cnt = self.decision_engine._last_decision_candidates
            self.game_recorder.record_decision(
                act_index, selected_action,
                score=_score, layer=_layer,
                candidates_count=_candidates_cnt,
                context=ctx)
            
            # Validate action index
            if not self.validate_action(act_index, action_list):
                self.logger.error(f"Invalid action index: {act_index}, using 0")
                act_index = 0
            
            await self.send_action(act_index)
            
        except Exception as e:
            self.logger.error(f"✗ Decision error: {e}", exc_info=True)
            await self.send_action(0)
    
    def _extract_tribute_back_card(self, selected):
        """
        GUA-086: 从平台 act 消息的 actionList 项 ["tribute"|"back", "tribute"|"back", [card_str,...]]
        提取送出的单张牌字符串。参考 scripts/tools/yf_replay.py:59 _cards_from_tribute_back_action。
        """
        if not isinstance(selected, list) or len(selected) < 3:
            return None
        cards = selected[2]
        if isinstance(cards, list) and cards:
            first = cards[0]
            if isinstance(first, str) and len(first) >= 2:
                return first[0].upper() + first[1:].upper()
        return None

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
        # GUA-086: 送出进贡 → 提取单张牌再调 adjust_initial_hand_for_tribute_back
        tribute_card = self._extract_tribute_back_card(selected)
        self.game_recorder.adjust_initial_hand_for_tribute_back(tribute_card, "remove")
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
        # GUA-086: 送出还牌 → 提取单张牌再调 adjust_initial_hand_for_tribute_back
        back_card = self._extract_tribute_back_card(selected)
        self.game_recorder.adjust_initial_hand_for_tribute_back(back_card, "remove")
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
        """Send action to server
        V8 (openguandan): 发送完整 action 三元组，区分 PLAY/TRIBUTE/PAYTRIBUTE
        V7 (v1006): 发送 {"actIndex": N}
        """
        try:
            if self.platform == "openguandan" and self.adapter:
                act_tuple = self.last_action_list[action_index] if action_index < len(self.last_action_list) else ["PASS", "PASS", ["PASS"]]
                if self.last_stage == "tribute":
                    message = self.adapter.tribute_action(act_tuple)
                elif self.last_stage == "back":
                    message = self.adapter.pay_tribute_action(
                        act_tuple,
                        self.last_tribute_pos or 0,
                        self.last_tribute_card or "",
                    )
                else:
                    message = self.adapter.play_action(act_tuple)
                self.logger.info(f"发送动作: {self.last_stage} act={act_tuple}")
            else:
                message = {"actIndex": action_index}
                self.logger.info(f"发送动作: actIndex={action_index}")

        except Exception as e:
            self.logger.error(f"✗ Send action error: {e}", exc_info=True)


async def main():
    """Main function — V8 支持 --platform / --role / --games 参数"""
    import argparse
    parser = argparse.ArgumentParser(description="yf2_v8 client (OpenGuanDan)")
    parser.add_argument("--platform", choices=["v1006", "openguandan"], default="v1006")
    parser.add_argument("--role", choices=["creator", "joiner"], default=None)
    parser.add_argument("--games", type=int, default=1)
    args = parser.parse_args()
    
    v8_role = args.role if args.platform == "openguandan" else None
    client = YF2_V8_Client(
        platform=args.platform,
        v8_role=v8_role or "joiner",
        v8_round_count=args.games,
    )
    await client.connect()


if __name__ == "__main__":
    asyncio.run(main())
