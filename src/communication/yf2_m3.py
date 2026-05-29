# -*- coding: utf-8 -*-
"""
yf2_m3 - YiFei AI M3 Client (Player 2)
M3版本：忠实移植lalala决策引擎
"""

import asyncio
import json
import sys
import logging
from pathlib import Path
import time
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from m.m3 import M3DecisionEngine
from communication.game_recorder import (
    GameRecorder,
    normalize_cards_to_string_list,
    ensure_my_pos_int,
)
from communication.websocket_manager import WebSocketManager
try:
    from game_logic.guandan_constants import CARDS_PER_PLAYER
except ImportError:
    CARDS_PER_PLAYER = 27

log_dir = Path(__file__).parent.parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

log_filename = log_dir / f"yf2_m3_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

DELAY_BEFORE_CONNECT = 7


class YF2_M3_Client:

    def __init__(self, player_id=2, use_local_websocket=True):
        self.player_id = player_id
        self.user_info = "yf2_m3"
        self.logger = logging.getLogger("yf2_m3")

        self.ws_manager = WebSocketManager(self.user_info, use_local=use_local_websocket)
        self.websocket = None

        self.logger.info("Initializing M3DecisionEngine (lalala port)")
        self.decision_engine = M3DecisionEngine(player_id)

        self.hand_cards = []
        self.decision_count = 0
        self.game_count = 0

        self.game_recorder = GameRecorder(player_id, "yf2_m3")
        self.pending_result_files = []

        self.round_counter = 0
        self.current_self_rank = None
        self.current_oppo_rank = None
        self.current_cur_rank = "2"

        self.logger.info("yf2_m3 initialized (Player {})".format(player_id))

    async def connect(self):
        try:
            self.logger.info("[yf2_m3] 等待连接延迟 {} 秒...".format(DELAY_BEFORE_CONNECT))
            time.sleep(DELAY_BEFORE_CONNECT)
            self.logger.info("[yf2_m3] 开始连接 ws://127.0.0.1:23456/game/yf2_m3")
            connected = await self.ws_manager.connect()
            if not connected:
                self.logger.error("Failed to connect to server")
                return

            self.websocket = self.ws_manager.websocket

            print("[yf2_m3] 连接成功！期望位置：{}号位".format(self.player_id))

            self.ws_manager.set_message_handler(self.process_message)

            await self.ws_manager.handle_messages()
        except Exception as e:
            self.logger.error("Connection error: {}".format(e), exc_info=True)

    async def process_message(self, data: dict):
        message_type = data.get("type", "")
        try:
            action_idx = self.decision_engine.on_message(data)

            if message_type == "notify":
                self._handle_notification(data)
            elif message_type == "act":
                self._handle_act(data)

            if message_type == "act" and action_idx >= 0:
                action_list = data.get("actionList") or []
                if not action_list:
                    self.logger.warning("act message without actionList, skip send")
                    return
                action_idx = max(0, min(action_idx, len(action_list) - 1))
                await self.send_action(action_idx)

        except Exception as e:
            self.logger.error("process_message error: {}".format(e), exc_info=True)
            if message_type == "act":
                action_list = data.get("actionList") or []
                if action_list:
                    await self.send_action(0)

    def _handle_notification(self, data: dict):
        notify_type = data.get("notifyType", "")
        stage = data.get("stage", "")
        notification_key = notify_type if notify_type else stage

        if notification_key in ("gameStart", "beginning"):
            self._handle_game_start(data)
        elif notification_key in ("gameOver", "gameResult", "episodeOver"):
            data["notification_key"] = notification_key
            self._handle_game_over(data)

    def _handle_act(self, data: dict):
        self.decision_count += 1

        act_self = data.get("selfRank")
        act_oppo = data.get("oppoRank")
        act_cur = data.get("curRank")
        if act_self is not None:
            self.current_self_rank = str(act_self)
        if act_oppo is not None:
            self.current_oppo_rank = str(act_oppo)
        if act_cur is not None:
            self.current_cur_rank = str(act_cur)

        if not self.game_recorder.current_game:
            raw_hand = data.get("handCards", [])
            hand_cards = normalize_cards_to_string_list(raw_hand)
            if hand_cards and len(hand_cards) == CARDS_PER_PLAYER:
                my_pos = data.get("myPos", self.player_id)
                self.hand_cards = hand_cards
                all_players_hands = {}
                public_info = data.get("publicInfo", [])
                if public_info and isinstance(public_info, list):
                    for i, info in enumerate(public_info):
                        if isinstance(info, dict) and "handCards" in info:
                            player_hand = normalize_cards_to_string_list(info["handCards"])
                            if player_hand:
                                all_players_hands[i] = player_hand
                all_players_hands[my_pos] = hand_cards
                game_info = {
                    "selfRank": data.get("selfRank"),
                    "oppoRank": data.get("oppoRank"),
                    "curRank": data.get("curRank", "2"),
                }
                self.game_recorder.start_game(hand_cards, my_pos, game_info, all_players_hands)
                self.game_count += 1

    def _handle_game_start(self, data: dict):
        hand_cards = normalize_cards_to_string_list(data.get("handCards", []) or data.get("initial_hand", []))
        my_pos = ensure_my_pos_int(data, self.player_id)
        if my_pos != self.player_id:
            self.logger.info("Position updated: {} -> {}".format(self.player_id, my_pos))
            self.player_id = my_pos
            self.decision_engine = M3DecisionEngine(my_pos)
        self.logger.info("Game start, I am position {}, hand cards count: {}".format(my_pos, len(hand_cards)))
        self.hand_cards = hand_cards

        self.round_counter += 1
        beg_self = data.get("selfRank")
        beg_oppo = data.get("oppoRank")
        beg_cur = data.get("curRank")
        if beg_self is not None:
            self.current_self_rank = str(beg_self)
        if beg_oppo is not None:
            self.current_oppo_rank = str(beg_oppo)
        if beg_cur is not None:
            self.current_cur_rank = str(beg_cur)

        all_players_hands = {}
        public_info = data.get("publicInfo", [])
        if public_info and isinstance(public_info, list):
            for i, info in enumerate(public_info):
                if isinstance(info, dict) and "handCards" in info:
                    player_hand = normalize_cards_to_string_list(info["handCards"])
                    if player_hand:
                        all_players_hands[i] = player_hand
        all_players_hands[my_pos] = hand_cards
        game_info = {
            "selfRank": self.current_self_rank,
            "oppoRank": self.current_oppo_rank,
            "curRank": self.current_cur_rank,
        }
        self.game_recorder.start_game(hand_cards, my_pos, game_info, all_players_hands)
        self.game_count += 1

    def _determine_game_result(self, order: list):
        if self.player_id not in order or len(order) < 4:
            return "unknown"
        partner_pos = (self.player_id + 2) % 4
        my_finish = order.index(self.player_id)
        partner_finish = order.index(partner_pos)
        our_best = min(my_finish, partner_finish)
        if our_best == 0:
            return "win"
        if our_best == 1:
            worst = max(my_finish, partner_finish)
            return "draw" if worst == 2 else "loss"
        return "loss"

    def _handle_game_over(self, data: dict):
        self.game_count += 1

        order = data.get("order")
        if order and isinstance(order, list) and len(order) >= 4:
            result_label = self._determine_game_result(order)
            self.logger.info("本局结果: %s (yf1_m3 负责写入 score 文件)", result_label)

        result_data = data.get("result", [])
        if isinstance(result_data, list) and len(result_data) >= 5:
            victory_num = result_data[4] if len(result_data) > 4 else []
            result = {"victoryNum": victory_num} if victory_num else {}
        else:
            result = data.get("result", {})
            if not isinstance(result, dict):
                result = {}
        if not result.get("victoryNum"):
            result["victoryNum"] = data.get("victoryNum", [])
        victory_num = result.get("victoryNum", [])
        has_victory = isinstance(victory_num, list) and len(victory_num) >= 4
        if has_victory:
            self.logger.info("Game {} over, victoryNum: {}".format(self.game_count, victory_num))
        if self.game_recorder.current_game:
            filepath = self.game_recorder.end_game(result)
            if filepath:
                if has_victory:
                    self.logger.info("Game record saved: {}".format(filepath))
                else:
                    self.pending_result_files.append(str(filepath))
        else:
            if has_victory:
                self._flush_pending_records(result)
        if has_victory:
            self._flush_pending_records(result)

    def _flush_pending_records(self, result: dict):
        victory_num = result.get("victoryNum", [])
        if victory_num:
            updated = self.game_recorder.backfill_victory_num(victory_num, self.pending_result_files)
            if updated:
                self.logger.info("已回填 {} 个 pending 记录".format(updated))

    async def send_action(self, action_idx: int):
        try:
            message = {"type": "act", "actIndex": action_idx}
            await self.ws_manager.send_json(message)
            self.logger.debug("Sent action: {}".format(action_idx))
        except Exception as e:
            self.logger.error("Failed to send action: {}".format(e), exc_info=True)


async def main():
    client = YF2_M3_Client(player_id=2)
    await client.connect()


if __name__ == "__main__":
    asyncio.run(main())
