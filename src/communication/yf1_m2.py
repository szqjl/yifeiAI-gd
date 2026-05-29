# -*- coding: utf-8 -*-
"""
yf1_m2 - YiFei AI M2 Client (Player 0)
M2版本：重构的硬编码规则引擎，无分数累积+阈值保护

与 M1 核心区别：
- 保护逻辑内联在按牌型分发的处理器中（lalala 风格）
- 不加载共享 TeammateProtectionStrategy（分数累积式）
- PASS 次数降级链完整
- 队友剩牌≤4 时只出刚好大1
- 开局主动恢复一手出完检查
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

from m.m2 import RuleBasedDecisionEngineM2
from communication.game_recorder import (
    GameRecorder,
    normalize_cards_to_string_list,
    normalize_action_list,
    ensure_my_pos_int,
    sync_pass_counters,
)
from communication.websocket_manager import WebSocketManager
try:
    from game_logic.guandan_constants import CARDS_PER_PLAYER, DEFAULT_REST_CARDS
except ImportError:
    CARDS_PER_PLAYER = 27
    DEFAULT_REST_CARDS = 27

import os

log_dir = Path(__file__).parent.parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

log_filename = log_dir / f"yf1_m2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

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


class YF1_M2_Client:
    """
    YiFei AI M2 Client - Player 0
    M2版本：重构硬编码规则引擎
    """

    def __init__(self, player_id=0, use_local_websocket=True):
        self.player_id = player_id
        self.user_info = "yf1_m2"
        self.logger = logging.getLogger(f"yf1_m2")

        self.ws_manager = WebSocketManager(self.user_info, use_local=use_local_websocket)
        self.websocket = None

        self.logger.info("Initializing RuleBasedDecisionEngineM2")
        config = {
            "max_decision_time": 0.8,
            "enable_logging": True,
        }
        self.decision_engine = RuleBasedDecisionEngineM2(player_id, config)

        self.hand_cards = []

        self.pass_num = 0
        self.my_pass_num = 0

        self.decision_count = 0
        self.game_count = 0

        self.game_recorder = GameRecorder(player_id, "yf1_m2")
        self.pending_result_files = []

        # 等级追踪
        self.round_counter = 0
        self.current_self_rank = None
        self.current_oppo_rank = None
        self.current_cur_rank = "2"
        self.current_game_start_round = 1
        self.current_game_rounds = []

        self.logger.info("yf1_m2 initialized (Player {})".format(player_id))
        self.logger.info("  - Decision Engine: RuleBasedDecisionEngineM2")
        self.logger.info("  - Series: M2 (Hardcoded Rules, refactored)")
        self.logger.info("  - Protection: inline lalala-style (no score accumulation)")

    async def connect(self):
        try:
            self.logger.info("[yf1_m2] 等待连接延迟 {} 秒，确保第一个位置...".format(DELAY_BEFORE_CONNECT))
            time.sleep(DELAY_BEFORE_CONNECT)
            self.logger.info("[yf1_m2] 开始连接 ws://127.0.0.1:23456/game/yf1_m2")
            connected = await self.ws_manager.connect()
            if not connected:
                self.logger.error("Failed to connect to server")
                return

            self.websocket = self.ws_manager.websocket

            print("[yf1_m2] 连接成功！期望位置：{}号位（实际位置将在游戏开始时由服务器分配）".format(self.player_id))
            self.logger.info("Connected to server. Expected position: {} (actual position will be assigned by server at game start)".format(self.player_id))

            self.ws_manager.set_message_handler(self.process_message)

            await self.ws_manager.handle_messages()
        except Exception as e:
            self.logger.error("Connection error: {}".format(e), exc_info=True)

    async def handle_messages(self):
        await self.ws_manager.handle_messages(self.process_message)

    async def process_message(self, data: dict):
        message_type = data.get("type", "")

        if message_type == "act":
            await self.handle_action_request(data)
        elif message_type == "notify":
            self.handle_notification(data)

    def _handle_tribute_notification(self, data: dict):
        result = data.get("result", [])
        if result:
            for tribute_result in result:
                if len(tribute_result) >= 3:
                    tribute_pos, receive_tribute_pos, card = tribute_result
                    print("{}号位进贡给{}号位牌{}".format(tribute_pos, receive_tribute_pos, card))

    def _handle_back_notification(self, data: dict):
        result = data.get("result", [])
        if result:
            for back_result in result:
                if len(back_result) >= 3:
                    back_pos, receive_back_pos, card = back_result
                    print("{}号位还贡给{}号位牌{}".format(back_pos, receive_back_pos, card))

    def _handle_tribute_action(self, data: dict):
        self_rank = data.get("selfRank")
        oppo_rank = data.get("oppoRank")
        cur_rank = data.get("curRank")
        if self_rank is not None:
            self.current_self_rank = str(self_rank)
        if oppo_rank is not None:
            self.current_oppo_rank = str(oppo_rank)
        if cur_rank is not None:
            self.current_cur_rank = str(cur_rank)
        print("我方等级：{}， 对方等级：{}， 当前等级{}".format(self.current_self_rank, self.current_oppo_rank, self.current_cur_rank))

        action_list = data.get("actionList", {})
        if "tribute" in action_list:
            tribute_cards = action_list["tribute"]
            print("轮到自己进贡，可以进贡的牌有:")
            print(tribute_cards)

    def _handle_back_action(self, data: dict):
        self_rank = data.get("selfRank")
        oppo_rank = data.get("oppoRank")
        cur_rank = data.get("curRank")
        if self_rank is not None:
            self.current_self_rank = str(self_rank)
        if oppo_rank is not None:
            self.current_oppo_rank = str(oppo_rank)
        if cur_rank is not None:
            self.current_cur_rank = str(cur_rank)
        print("我方等级：{}， 对方等级：{}， 当前等级{}".format(self.current_self_rank, self.current_oppo_rank, self.current_cur_rank))

        action_list = data.get("actionList", {})
        if "back" in action_list:
            back_cards = action_list["back"]
            print("轮到自己还贡，可以还贡的牌有:")
            print(back_cards)

    def handle_notification(self, data: dict):
        notify_type = data.get("notifyType", "")
        stage = data.get("stage", "")
        notification_key = notify_type if notify_type else stage
        self.logger.debug("收到通知: notifyType={}, stage={}, notification_key={}".format(notify_type, stage, notification_key))
        if notification_key in ("gameStart", "beginning"):
            self._handle_game_start(data)
        elif notification_key in ("gameOver", "gameResult", "episodeOver"):
            data["notification_key"] = notification_key
            self._handle_game_over(data)
        elif notification_key == "tribute":
            self._handle_tribute_notification(data)
        elif notification_key == "back":
            self._handle_back_notification(data)
        elif notification_key == "play":
            pass
        else:
            if "gameOver" in data or "gameResult" in data or "episodeOver" in data or data.get("result"):
                self.logger.info("从其他字段识别到游戏结束: notifyType={}, stage={}".format(notify_type, stage))
                self._handle_game_over(data)
            else:
                self.logger.warning("未识别的通知类型: notifyType={}, stage={}, notification_key={}".format(notify_type, stage, notification_key))

    def _handle_game_start(self, data: dict):
        hand_cards = normalize_cards_to_string_list(data.get("handCards", []) or data.get("initial_hand", []))
        my_pos = ensure_my_pos_int(data, self.player_id)
        if my_pos != self.player_id:
            self.logger.info("Position updated: {} -> {}".format(self.player_id, my_pos))
            self.player_id = my_pos
            config = {"max_decision_time": 0.8, "enable_logging": True}
            self.decision_engine = RuleBasedDecisionEngineM2(my_pos, config)
        self.logger.info("Game start, I am position {}, hand cards count: {}".format(my_pos, len(hand_cards)))
        self.hand_cards = hand_cards
        self.pass_num = 0
        self.my_pass_num = 0

        self.round_counter += 1
        # 尝试从 beginning 通知获取等级（实际等级在 act 消息里更准确，这里取不到则沿用上次）
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
        self.logger.info("Game recording started: game_count={}, players={}, selfRank={}, oppoRank={}, curRank={}".format(
            self.game_count, len(all_players_hands), self.current_self_rank, self.current_oppo_rank, self.current_cur_rank))

    SCORE_FILE = str(Path(__file__).parent.parent.parent / "game_scores_m2.json")

    def _level_num(self, lv):
        """等级转数值，用于比较"""
        m = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8,
             "9": 9, "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14}
        return m.get(str(lv).upper(), 0)

    def _detect_game_end(self, order: list, prev_self_rank: str, prev_oppo_rank: str) -> str:
        """检测本轮结束后是否完成了完整的一局（2→A+双上）。
        返回: 'win', 'loss', 'draw', None
        """
        if order is None or len(order) < 4:
            return None
        partner_pos = (self.player_id + 2) % 4
        my_finish = order.index(self.player_id)
        partner_finish = order.index(partner_pos)

        # 我方在A级且双上 → 我局胜
        if prev_self_rank == "A" and my_finish == 0 and partner_finish == 1:
            return "win"
        # 对方在A级且双上 → 我局负
        if prev_oppo_rank == "A":
            oppo_positions = [i for i in range(4) if i != self.player_id and i != partner_pos]
            if all(order.index(op) < 2 for op in oppo_positions):
                return "loss"
        return None

    def _determine_round_result(self, order: list) -> str:
        """从 episodeOver 的 order (完赛名次) 推断本轮胜负。
        order = [头游player, 二游player, 三游player, 四游player]
        返回 'win', 'draw', 'loss' 之一。
        """
        if self.player_id not in order or len(order) < 4:
            return "unknown"
        partner_pos = (self.player_id + 2) % 4
        my_finish = order.index(self.player_id)
        partner_finish = order.index(partner_pos)
        our_best = min(my_finish, partner_finish)
        self.logger.info(
            "完赛名次 order=%s, my_pos=%d finish=%d, partner=%d finish=%d, best=%d",
            order, self.player_id, my_finish, partner_pos, partner_finish, our_best,
        )
        if our_best == 0:
            return "win"
        if our_best == 1:
            worst = max(my_finish, partner_finish)
            return "draw" if worst == 2 else "loss"
        return "loss"

    def _save_round_result(self, result_label: str, order: list) -> dict:
        """将本轮结果写入 game_scores_m2.json，含等级追踪和整局检测。
        返回 scores 字典。
        """
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

        # 记录本轮
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

        # 检测是否完成一局
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
                "★★★ 整局结束 ★★★ Game=%d (rounds %d-%d), %s",
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
            "本轮 %s  →  副 %d/%d (胜 %.1f%%)  局 %d/%d (胜 %.1f%%)",
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
        self.logger.info("处理游戏结束通知: notification_key={}".format(notification_key))

        # 从 episodeOver 的 order 字段跟踪本轮胜负/等级
        order = data.get("order")
        if order and isinstance(order, list) and len(order) >= 4:
            result_label = self._determine_round_result(order)
            self._save_round_result(result_label, order)

        result_data = data.get("result", [])
        # 兼容不同格式：提取为字典格式 result
        if isinstance(result_data, list) and len(result_data) >= 5:
            victory_num = result_data[4] if len(result_data) > 4 else []
            result = {"victoryNum": victory_num} if victory_num else {}
        else:
            result = data.get("result", {})
            if not isinstance(result, dict):
                result = {}
        # 兼容部分服务器将 victoryNum 放在顶层
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
                    self.logger.warning("Game record saved without victoryNum, pending backfill: {}".format(filepath))
        else:
            self.logger.info("游戏结束通知但current_game为空: notification_key={}".format(notification_key))
            # 如果 result 有 victoryNum，回填 pending 记录
            if has_victory:
                self._flush_pending_records(result)
        # 如果本次有完整 victoryNum，回填之前空结果的文件
        if has_victory:
            self._flush_pending_records(result)
        self.pass_num = 0
        self.my_pass_num = 0

    def _handle_game_result(self, data: dict):
        result = data.get("result", {})
        if not isinstance(result, dict):
            result = {}
        victory_num = result.get("victoryNum", [])
        has_victory = isinstance(victory_num, list) and len(victory_num) >= 4
        if has_victory:
            self.logger.info("Game result victoryNum: {}".format(victory_num))
            if self.game_recorder.current_game:
                filepath = self.game_recorder.end_game(result)
                if filepath:
                    self.logger.info("Game record saved from result: {}".format(filepath))
            self._flush_pending_records(result)
        else:
            self.game_recorder.backfill_victory_num(victory_num, self.pending_result_files)

    def _flush_pending_records(self, result: dict):
        victory_num = result.get("victoryNum", [])
        if victory_num:
            updated = self.game_recorder.backfill_victory_num(victory_num, self.pending_result_files)
            if updated:
                self.logger.info("已回填 {} 个 pending 记录的 victoryNum".format(updated))

    async def handle_action_request(self, data: dict):
        try:
            self.decision_count += 1

            # 从 act 消息捕获最新等级
            act_self = data.get("selfRank")
            act_oppo = data.get("oppoRank")
            act_cur = data.get("curRank")
            if act_self is not None:
                self.current_self_rank = str(act_self)
            if act_oppo is not None:
                self.current_oppo_rank = str(act_oppo)
            if act_cur is not None:
                self.current_cur_rank = str(act_cur)

            # 检查是否是游戏开始（如果还没有开始记录）
            if not self.game_recorder.current_game:
                raw_hand = data.get("handCards", [])
                hand_cards = normalize_cards_to_string_list(raw_hand)
                if hand_cards and len(hand_cards) == CARDS_PER_PLAYER:
                    self.logger.info("在action请求中检测到初始手牌，触发游戏开始")
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
                    self.logger.info("Game recording started (from action request): game_count={}, players={}".format(self.game_count, len(all_players_hands)))

            action_list = data.get("actionList", [])
            handcards = data.get("handCards", [])

            # 同步 PASS 计数器
            cur_action = data.get("curAction") or []
            cur_pos = data.get("curPos", -1)
            self.pass_num, self.my_pass_num = sync_pass_counters(
                self.pass_num, self.my_pass_num, cur_action, cur_pos, self.player_id
            )

            message = {
                "actionList": action_list,
                "handCards": handcards,
                "myPos": self.player_id,
                "curAction": cur_action,
                "stage": "play",
                "publicInfo": data.get("publicInfo", []),
                "curRank": data.get("curRank", "2"),
                "pass_num": self.pass_num,
                "my_pass_num": self.my_pass_num,
                "greaterPos": data.get("greaterPos", -1),
                "curPos": data.get("curPos", -1),
            }

            handcards_copy = list(handcards) if handcards else []
            action_idx = self.decision_engine.decide(message)

            if isinstance(action_idx, int) and 0 <= action_idx < len(action_list):
                selected_action = action_list[action_idx]
            else:
                selected_action = ["PASS"]
                action_idx = 0

            # 更新 PASS 计数
            if isinstance(selected_action, list) and len(selected_action) > 0:
                if selected_action[0] == "PASS":
                    self.pass_num += 1
                    self.my_pass_num += 1
                else:
                    self.pass_num = 0
                    if cur_action:
                        self.my_pass_num = 0
            elif selected_action == "PASS":
                self.pass_num += 1
                self.my_pass_num += 1
            else:
                self.pass_num = 0
                self.my_pass_num = 0

            await self.send_action(action_idx)

            self.game_recorder.record_decision(
                action_idx,
                selected_action,
                context={"decision_count": self.decision_count}
            )

        except Exception as e:
            self.logger.error("Handle action error: {}".format(e), exc_info=True)
            await self.send_action(0)

    async def send_action(self, action_idx: int):
        try:
            message = {"type": "act", "actIndex": action_idx}
            await self.ws_manager.send_json(message)
            self.logger.debug("Sent action: {}".format(action_idx))
        except Exception as e:
            self.logger.error("Failed to send action: {}".format(e), exc_info=True)


async def main():
    client = YF1_M2_Client(player_id=0)
    await client.connect()


if __name__ == "__main__":
    asyncio.run(main())
