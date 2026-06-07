# -*- coding: utf-8 -*-
"""
yf1_m3 - YiFei AI M3 Client (Player 0)
M3 主交付客户端：M3DecisionEngine
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
from communication.game_result_utils import (
    build_game_result_payload,
    build_latest_victory_num_payload,
    build_local_batch_victory_num,
    resolve_expected_batch_games,
    validate_batch_victory_num,
)
from communication.websocket_manager import WebSocketManager
from game_logic.platform_act import clamp_act_index
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

        self.logger.info("Initializing M3DecisionEngine")
        self.decision_engine = M3DecisionEngine(player_id)

        self.hand_cards = []
        self.decision_count = 0
        self.game_count = 0

        self.game_recorder = GameRecorder(player_id, "yf1_m3")
        self.pending_result_files = []
        self._batch_setting_times = None
        self._batch_platform_wins = [0, 0]
        self._last_episode_order = None
        self._project_root = Path(__file__).parent.parent.parent

        # 等级追踪
        self.round_counter = 0
        self.current_self_rank = None
        self.current_oppo_rank = None
        self.current_cur_rank = "2"
        self.current_game_start_round = 1

        self.logger.info("yf1_m3 initialized (Player {})".format(player_id))
        self.logger.info("  - Decision Engine: M3DecisionEngine")

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
                action_idx = clamp_act_index(action_idx, action_list, data.get("indexRange"))
                selected_action = action_list[action_idx]
                self.game_recorder.record_decision(
                    action_idx,
                    selected_action,
                    context=self._decision_context_from_act(data),
                )
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
        elif notification_key == "tribute":
            self._handle_tribute_notification(data)
        elif notification_key == "back":
            self._handle_back_notification(data)
        elif notification_key == "act" or (stage == "play" and notify_type == ""):
            self._handle_act_notification(data)

    def _normalize_tribute_back_card(self, card):
        """贡/还牌单张 → 'S2' 大写字符串（与 normalize_cards_to_string_list 一致）。"""
        if card is None:
            return None
        normalized = normalize_cards_to_string_list([card])
        if not normalized:
            return None
        raw = normalized[0]
        if isinstance(raw, str) and len(raw) >= 2:
            return raw[0].upper() + raw[1:].upper()
        return raw

    def _decision_context_from_act(self, data: dict) -> dict:
        return {
            "myPos": data.get("myPos", self.player_id),
            "curPos": data.get("curPos", -1),
            "greaterPos": data.get("greaterPos", -1),
            "actionList_size": len(data.get("actionList") or []),
            "selfRank": data.get("selfRank", self.current_self_rank),
            "oppoRank": data.get("oppoRank", self.current_oppo_rank),
            "curRank": data.get("curRank", self.current_cur_rank),
            "version": "m3",
            "series": "M",
            "source": "act",
            "stage": data.get("stage", ""),
        }

    def _already_recorded_back(self, card_str):
        for md in self.game_recorder.current_game.get("my_decisions", []) if self.game_recorder.current_game else []:
            action = md.get("action") or []
            if len(action) >= 3 and str(action[0]).lower() == "back":
                existing = action[2]
                if isinstance(existing, list) and card_str in existing:
                    return True
        return False

    def _already_recorded_tribute_received(self, card_str, tribute_pos):
        for md in self.game_recorder.current_game.get("my_decisions", []) if self.game_recorder.current_game else []:
            action = md.get("action") or []
            ctx = md.get("context") or {}
            if len(action) >= 3 and str(action[0]).lower() == "tribute":
                existing = action[2]
                if (
                    isinstance(existing, list)
                    and card_str in existing
                    and ctx.get("source") == "notify"
                    and ctx.get("receive_tribute_pos") == self.player_id
                    and ctx.get("tribute_pos") == tribute_pos
                ):
                    return True
        return False

    def _handle_tribute_notification(self, data: dict):
        """进贡 notify：收贡方写入 my_decisions；进贡方 outgoing 已由 act 录牌。"""
        result = data.get("result") or []
        for item in result:
            if not isinstance(item, (list, tuple)) or len(item) < 3:
                continue
            tribute_pos, receive_pos, card = item[0], item[1], item[2]
            try:
                tribute_pos_i = int(tribute_pos)
                receive_pos_i = int(receive_pos)
            except (TypeError, ValueError):
                continue
            card_str = self._normalize_tribute_back_card(card)
            self.logger.info(
                "进贡 notify: %s -> %s 牌 %s",
                tribute_pos_i, receive_pos_i, card_str or card,
            )
            if receive_pos_i != self.player_id:
                continue
            if tribute_pos_i == self.player_id:
                continue
            if not card_str:
                continue
            if not self.game_recorder.current_game:
                self.logger.warning("进贡 notify 时无 current_game，跳过录牌: %s", card_str)
                continue
            if self._already_recorded_tribute_received(card_str, tribute_pos_i):
                self.logger.info("收进贡已记录，跳过重复: %s", card_str)
                continue
            self.game_recorder.record_decision(
                0,
                ["tribute", "tribute", [card_str]],
                context={
                    "myPos": self.player_id,
                    "curPos": -1,
                    "greaterPos": -1,
                    "actionList_size": 0,
                    "selfRank": self.current_self_rank,
                    "oppoRank": self.current_oppo_rank,
                    "curRank": self.current_cur_rank,
                    "version": "m3",
                    "series": "M",
                    "source": "notify",
                    "stage": "tribute",
                    "tribute_pos": tribute_pos_i,
                    "receive_tribute_pos": receive_pos_i,
                },
            )
            self.logger.info("已录收进贡（notify）: %s from pos %s", card_str, tribute_pos_i)

    def _handle_back_notification(self, data: dict):
        """还贡 notify：对手还给我的牌写入 my_decisions（我方主动还贡仍走 act 录牌）。"""
        result = data.get("result") or []
        for item in result:
            if not isinstance(item, (list, tuple)) or len(item) < 3:
                continue
            back_pos, receive_pos, card = item[0], item[1], item[2]
            try:
                receive_pos = int(receive_pos)
            except (TypeError, ValueError):
                continue
            card_str = self._normalize_tribute_back_card(card)
            if not card_str:
                continue
            self.logger.info(
                "还贡 notify: %s -> %s 牌 %s", back_pos, receive_pos, card_str
            )
            if receive_pos != self.player_id:
                continue
            if not self.game_recorder.current_game:
                self.logger.warning("还贡 notify 时无 current_game，跳过录牌: %s", card_str)
                continue
            if self._already_recorded_back(card_str):
                self.logger.info("还贡已记录，跳过重复: %s", card_str)
                continue
            self.game_recorder.record_decision(
                0,
                ["back", "back", [card_str]],
                context={
                    "myPos": self.player_id,
                    "curPos": -1,
                    "greaterPos": -1,
                    "actionList_size": 0,
                    "selfRank": self.current_self_rank,
                    "oppoRank": self.current_oppo_rank,
                    "curRank": self.current_cur_rank,
                    "version": "m3",
                    "series": "M",
                    "source": "notify",
                    "stage": "back",
                    "back_pos": back_pos,
                    "receive_back_pos": receive_pos,
                },
            )
            self.logger.info("已录还贡（notify）: %s", card_str)

    def _handle_act_notification(self, data: dict):
        hand_cards = data.get("handCards", [])
        if hand_cards:
            if len(hand_cards) <= CARDS_PER_PLAYER:
                self.hand_cards = normalize_cards_to_string_list(hand_cards)

        cur_pos = data.get("curPos", -1)
        cur_action = data.get("curAction", [])
        greater_pos = data.get("greaterPos", -1)
        greater_action = data.get("greaterAction", [])

        if cur_pos == -1 or not cur_action:
            return

        if isinstance(cur_action, str):
            try:
                import ast
                cur_action = ast.literal_eval(cur_action)
            except Exception:
                pass
        if isinstance(greater_action, str):
            try:
                import ast
                greater_action = ast.literal_eval(greater_action)
            except Exception:
                pass

        context = {
            "publicInfo": data.get("publicInfo", []),
            "selfRank": data.get("selfRank", self.current_self_rank),
            "oppoRank": data.get("oppoRank", self.current_oppo_rank),
            "curRank": data.get("curRank", self.current_cur_rank),
            "restCards": data.get("restCards", []),
        }
        self.game_recorder.record_action(cur_pos, cur_action, greater_pos, greater_action, context)

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
        stage = data.get("stage", "")
        notification_key = data.get("notification_key", "")

        # gameOver：仅记录 settingTimes，不写 victoryNum（对齐 M1 / GUA-008）
        if stage == "gameOver" or notification_key == "gameOver":
            st = data.get("settingTimes")
            if st is not None:
                self._batch_setting_times = int(st)
            expected = resolve_expected_batch_games(
                self._batch_setting_times, self._project_root
            )
            cur_times = data.get("curTimes")
            try:
                cur_times = int(cur_times) if cur_times is not None else None
            except (TypeError, ValueError):
                cur_times = None
            if (
                expected is not None
                and cur_times is not None
                and cur_times <= expected
                and self._last_episode_order
            ):
                label = self._determine_round_result(self._last_episode_order)
                if label == "win":
                    self._batch_platform_wins[0] += 1
                elif label == "loss":
                    self._batch_platform_wins[1] += 1
            self.logger.info(
                "gameOver: curTimes={}, settingTimes={}, batch_wins={}, expected={}".format(
                    data.get("curTimes"),
                    data.get("settingTimes"),
                    self._batch_platform_wins,
                    expected,
                )
            )
            return

        # episodeOver：副末 order / score；禁止从 result[4] 取批末 victoryNum
        if notification_key == "episodeOver" or stage == "episodeOver":
            order = data.get("order")
            if order and isinstance(order, list) and len(order) >= 4:
                self._last_episode_order = order
                result_label = self._determine_round_result(order)
                self._save_round_result(result_label, order)
            if self.game_recorder.current_game:
                filepath = self.game_recorder.end_game({})
                if filepath:
                    self.pending_result_files.append(str(filepath))
                    self.logger.info(
                        "episodeOver 落盘待回填: {} (pending={})".format(
                            filepath, len(self.pending_result_files)
                        )
                    )
            return

        # gameResult：RAW JSON + final/victoryNum
        if stage == "gameResult" or notification_key == "gameResult":
            self.logger.info(
                "gameResult RAW: %s", json.dumps(data, ensure_ascii=False)
            )
            result = build_game_result_payload(data)
            victory_num = result.get("victoryNum", [])
            server_vn_raw = list(victory_num) if victory_num else None
            vn_source = "server"
            expected = resolve_expected_batch_games(
                self._batch_setting_times, self._project_root
            )
            ok, reason = validate_batch_victory_num(victory_num, expected)
            if victory_num and not ok:
                local_vn = build_local_batch_victory_num(
                    self._batch_platform_wins[0],
                    self._batch_platform_wins[1],
                )
                ok_local, _ = validate_batch_victory_num(local_vn, expected)
                if ok_local:
                    self.logger.warning(
                        "gameResult 服务器 vn 无效(%s)，改用本批 gameOver 计数: %s",
                        reason,
                        local_vn,
                    )
                    victory_num = local_vn
                    result = {"victoryNum": local_vn}
                    vn_source = "fallback"
                    ok = True
            has_victory = bool(victory_num) and ok
            if victory_num and not ok:
                self.logger.warning(
                    "gameResult victoryNum 校验失败: %s (vn=%s, batch_games=%s)",
                    reason,
                    victory_num,
                    expected,
                )
                self.pending_result_files.clear()
                return

            if has_victory:
                self.logger.info("Game batch over, victoryNum: {}".format(victory_num))
                self._save_victory_num_to_shared_file(
                    victory_num,
                    expected,
                    server_vn_raw=server_vn_raw,
                    vn_source=vn_source,
                )

            if self.game_recorder.current_game:
                filepath = self.game_recorder.end_game(result if has_victory else {})
                if filepath:
                    if has_victory:
                        self.logger.info("Game record saved: {}".format(filepath))
                    else:
                        self.pending_result_files.append(str(filepath))
            if has_victory:
                self._flush_pending_records(result, expected)
            return

        self.logger.warning(
            "未识别的结束通知: stage={}, notification_key={}".format(
                stage, notification_key
            )
        )

    def _save_victory_num_to_shared_file(
        self,
        victory_num: list,
        batch_games=None,
        server_vn_raw=None,
        vn_source="server",
    ):
        try:
            shared_file = (
                Path(__file__).parent.parent.parent
                / "batch_executor"
                / "latest_victory_num.json"
            )
            shared_file.parent.mkdir(exist_ok=True)
            payload = build_latest_victory_num_payload(
                victory_num,
                batch_games,
                server_vn_raw=server_vn_raw,
                vn_source=vn_source,
                player="yf1_m3",
            )
            shared_file.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self.logger.info("victoryNum 已写入共享文件: {}".format(shared_file))
        except Exception as e:
            self.logger.warning("写入 latest_victory_num.json 失败: {}".format(e))

    def _flush_pending_records(self, result: dict, expected_batch_games=None):
        victory_num = result.get("victoryNum", [])
        if not victory_num:
            return
        updated = self.game_recorder.backfill_victory_num(
            victory_num,
            self.pending_result_files,
            expected_batch_games=expected_batch_games,
        )
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
