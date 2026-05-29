# -*- coding: utf-8 -*-
"""
yf1_m3 - YiFei AI M3 Client (Player 0)
M3版本：忠实移植lalala决策引擎，无分层架构，纯if-then决策树
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

log_filename = log_dir / f"yf1_m3_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

DELAY_BEFORE_CONNECT = 5


class YF1_M3_Client:

    def __init__(self, player_id=0, use_local_websocket=True):
        self.player_id = player_id
        self.user_info = "yf1_m3"
        self.logger = logging.getLogger("yf1_m3")

        self.ws_manager = WebSocketManager(self.user_info, use_local=use_local_websocket)
        self.websocket = None

        self.logger.info("Initializing M3DecisionEngine (lalala port)")
        self.decision_engine = M3DecisionEngine(player_id)

        self.hand_cards = []
        self.decision_count = 0
        self.game_count = 0

        self.game_recorder = GameRecorder(player_id, "yf1_m3")
        self.pending_result_files = []

        # 等级追踪
        self.round_counter = 0
        self.current_self_rank = None
        self.current_oppo_rank = None
        self.current_cur_rank = "2"
        self.current_game_start_round = 1

        self.logger.info("yf1_m3 initialized (Player {})".format(player_id))
        self.logger.info("  - Decision Engine: M3DecisionEngine (lalala faithful port)")

    async def connect(self):
        try:
            self.logger.info("[yf1_m3] 等待连接延迟 {} 秒...".format(DELAY_BEFORE_CONNECT))
            time.sleep(DELAY_BEFORE_CONNECT)
            self.logger.info("[yf1_m3] 开始连接 ws://127.0.0.1:23456/game/yf1_m3")
            connected = await self.ws_manager.connect()
            if not connected:
                self.logger.error("Failed to connect to server")
                return

            self.websocket = self.ws_manager.websocket

            print("[yf1_m3] 连接成功！期望位置：{}号位".format(self.player_id))

            self.ws_manager.set_message_handler(self.process_message)

            await self.ws_manager.handle_messages()
        except Exception as e:
            self.logger.error("Connection error: {}".format(e), exc_info=True)

    async def process_message(self, data: dict):
        try:
            # 1) 让M3引擎处理所有消息（更新状态 + 返回决策）
            action_idx = self.decision_engine.on_message(data)

            # 2) 处理游戏记录
            message_type = data.get("type", "")
            if message_type == "notify":
                self._handle_notification(data)
            elif message_type == "act":
                self._handle_act(data)

            # 3) 发送决策
            if action_idx >= 0:
                await self.send_action(action_idx)

        except Exception as e:
            self.logger.error("process_message error: {}".format(e), exc_info=True)
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
        elif notification_key == "tribute":
            pass
        elif notification_key == "back":
            pass

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
                self.logger.info("Detected initial hand in action request, starting game")
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
                    "selfRank": self.current_self_rank,
                    "oppoRank": self.current_oppo_rank,
                    "curRank": self.current_cur_rank,
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

    SCORE_FILE = str(Path(__file__).parent.parent.parent / "game_scores_m2.json")

    def _level_num(self, lv):
        m = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8,
             "9": 9, "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14}
        return m.get(str(lv).upper(), 0)

    def _detect_game_end(self, order: list, prev_self_rank: str, prev_oppo_rank: str):
        if order is None or len(order) < 4:
            return None
        partner_pos = (self.player_id + 2) % 4
        my_finish = order.index(self.player_id)
        partner_finish = order.index(partner_pos)

        if prev_self_rank == "A" and my_finish == 0 and partner_finish == 1:
            return "win"
        if prev_oppo_rank == "A":
            oppo_positions = [i for i in range(4) if i != self.player_id and i != partner_pos]
            if all(order.index(op) < 2 for op in oppo_positions):
                return "loss"
        return None

    def _determine_round_result(self, order: list):
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

    def _save_round_result(self, result_label: str, order: list):
        if result_label == "unknown":
            return {}
        score_path = Path(self.SCORE_FILE)
        try:
            scores = json.loads(score_path.read_text(encoding="utf-8")) if score_path.exists() else {}
        except Exception:
            scores = {}

        scores.setdefault("rounds", [])
        scores.setdefault("games", [])
        scores.setdefault("total_rounds", 0)
        scores.setdefault("round_wins", 0)
        scores.setdefault("round_draws", 0)
        scores.setdefault("round_losses", 0)
        scores.setdefault("total_games", 0)
        scores.setdefault("game_wins", 0)
        scores.setdefault("game_draws", 0)
        scores.setdefault("game_losses", 0)
        scores.setdefault("current_game_start_round", self.current_game_start_round)
        scores.setdefault("current_level_self", self.current_self_rank or "2")
        scores.setdefault("current_level_oppo", self.current_oppo_rank or "2")

        scores["total_rounds"] += 1
        round_entry = {
            "round": scores["total_rounds"],
            "order": order,
            "curRank": self.current_cur_rank,
            "selfRank": self.current_self_rank,
            "oppoRank": self.current_oppo_rank,
            "result": result_label,
        }
        scores["rounds"].append(round_entry)
        if result_label == "win":
            scores["round_wins"] += 1
        elif result_label == "draw":
            scores["round_draws"] += 1
        else:
            scores["round_losses"] += 1

        game_result = self._detect_game_end(
            order,
            self.current_self_rank or "2",
            self.current_oppo_rank or "2",
        )

        if game_result:
            scores["total_games"] += 1
            game_entry = {
                "game": scores["total_games"],
                "start_round": self.current_game_start_round,
                "end_round": scores["total_rounds"],
                "result": game_result,
            }
            scores["games"].append(game_entry)
            if game_result == "win":
                scores["game_wins"] += 1
            elif game_result == "draw":
                scores["game_draws"] += 1
            else:
                scores["game_losses"] += 1
            self.current_game_start_round = scores["total_rounds"] + 1
            self.logger.info(
                "整局结束 Game=%d (rounds %d-%d), %s",
                scores["total_games"], game_entry["start_round"], game_entry["end_round"], game_result,
            )

        scores["current_game_start_round"] = self.current_game_start_round
        scores["current_level_self"] = self.current_self_rank or "2"
        scores["current_level_oppo"] = self.current_oppo_rank or "2"

        rw = scores["round_wins"]
        rt = scores["total_rounds"]
        gw = scores["game_wins"]
        gt = scores["total_games"]
        self.logger.info(
            "本轮 %s  -> 副 %d/%d (胜 %.1f%%)  局 %d/%d (胜 %.1f%%)",
            result_label, rw, rt, rw / rt * 100 if rt else 0,
            gw, gt, gw / gt * 100 if gt else 0,
        )

        tmp = score_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(scores, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(score_path)
        return scores

    def _handle_game_over(self, data: dict):
        self.game_count += 1
        notification_key = data.get("notification_key", "")

        order = data.get("order")
        if order and isinstance(order, list) and len(order) >= 4:
            result_label = self._determine_round_result(order)
            self._save_round_result(result_label, order)

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
    client = YF1_M3_Client(player_id=0)
    await client.connect()


if __name__ == "__main__":
    asyncio.run(main())
