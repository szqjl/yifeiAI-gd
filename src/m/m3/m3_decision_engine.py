import copy
from random import random, randint
from .m3_utils import *
from game_logic.trick_state import resolve_effective_greater
from game_logic.platform_act import clamp_act_index, normalize_play_act_fields

ENG2CH = {
    "Single": "单张",
    "Pair": "对子",
    "Trips": "三张",
    "ThreePair": "三连对",
    "ThreeWithTwo": "三带二",
    "TripsPair": "三带对",
    "TwoTrips": "钢板",
    "Straight": "顺子",
    "StraightFlush": "同花顺",
    "Bomb": "炸弹",
    "PASS": "过"
}


class M3DecisionEngine:

    def __init__(self, player_id):
        self.player_id = player_id
        self._reset_state()

    def _dbg(self, msg: str):
        """Detailed debug for M3 PASS investigation.
        Outputs to both console (visible in client windows) and the standard log files.
        """
        print(f"[M3DBG-P{self.player_id}] {msg}")
        # Also send to the logging system so it appears in logs/yf1_m3_*.log and yf2_m3_*.log
        import logging
        logging.getLogger(f"M3.P{self.player_id}").info(f"[M3DBG] {msg}")

    def _ensure_list(self, val):
        """Safely convert possibly stringified action (e.g. "['Single', 'J', ['DJ']]") to Python list.
        This was the root cause of M3 always returning 0 (PASS) in passive dispatch.
        """
        if isinstance(val, (list, tuple)):
            return list(val)
        if isinstance(val, str):
            try:
                import ast
                parsed = ast.literal_eval(val)
                if isinstance(parsed, (list, tuple)):
                    return list(parsed)
            except Exception:
                pass
        return val

    def _uses_level_rank_cards(self, cards, rank_card):
        """任一牌点等于本级（含逢人配与同点 C/S/D/H）。"""
        rank_char = rank_card[-1]
        for card in cards:
            if card[-1] == rank_char:
                return True
        return False

    def _three_with_two_protect_ok(self, action_cards, bomb_member, rank_card):
        """GUA-026：三带二不拆炸弹、不消耗级牌。"""
        if len(set(action_cards) & set(bomb_member)) != 0:
            return False
        if self._uses_level_rank_cards(action_cards, rank_card):
            return False
        return True

    def _pick_three_with_two(
        self,
        three2_actionList,
        trip_member,
        pair_member,
        bomb_member,
        rank_card,
        card_val,
        *,
        allow_split_trips=False,
        split_trips_min_pair=10,
        prefer_low=True,
    ):
        """从合法三带二中选一手；优先不拆结构、不带级牌。"""
        ordered = sorted(
            three2_actionList,
            key=lambda item: card_val[item[1][1]],
            reverse=not prefer_low,
        )
        for tag, action in ordered:
            cards = action[2]
            if not self._three_with_two_protect_ok(cards, bomb_member, rank_card):
                continue
            trip = cards[0]
            pair = cards[3]
            if trip in trip_member and pair in pair_member and card_val[pair[-1]] <= 13:
                return tag
        if allow_split_trips:
            for tag, action in ordered:
                cards = action[2]
                if not self._three_with_two_protect_ok(cards, bomb_member, rank_card):
                    continue
                trip = cards[0]
                pair = cards[3]
                if trip in trip_member and pair in trip_member and card_val[pair[-1]] >= split_trips_min_pair:
                    return tag
        return -1

    def _is_teammate_greater(self, myPos, greaterPos):
        """GUA-029 R5：队友控牌时不炸。"""
        return (myPos + 2) % 4 == greaterPos

    def _gua031_passive_teammate_yield(self, myPos, greaterPos, numofmy):
        """GUA-031 P-F02：队友控牌且非残局冲刺（>10 张）→ 让道 PASS。"""
        if not self._is_teammate_greater(myPos, greaterPos):
            return False
        if numofmy <= 10:
            return False
        return True

    def _gua031_active_min_single(self, actionList, single_actionlist, card_val):
        """GUA-031 PASS-P02：队友剩 1 张 → 出最小 Single。"""
        if not single_actionlist:
            return -1
        for item in single_actionlist:
            card = item[1] if isinstance(item[1], str) else item[1][0]
            candidate = ["Single", item[0], [card]]
            try:
                return actionList.index(candidate)
            except ValueError:
                continue
        best_idx = -1
        best_val = 999
        for i, action in enumerate(actionList):
            if i == 0 or action[0] != "Single":
                continue
            val = card_val.get(action[1], 99)
            if val < best_val:
                best_val = val
                best_idx = i
        return best_idx

    def _gua031_filter_singles_for_next1(self, single_actionlist, card_val, numofnext):
        """GUA-031 PASS-P03：下家剩 1 张时禁过小单（< T）。"""
        if numofnext != 1:
            return single_actionlist
        floor = 10
        return [s for s in single_actionlist if card_val.get(s[0], 0) >= floor]

    def _gua031_active_feed_five(self, actionList, pair_actionlist, threetwo_actionlist, card_val, cur):
        """GUA-031 PASS-P04：队友剩 5 张 → 优先 Pair / ThreeWithTwo。"""
        pair_ceiling = cur[5]
        best_idx = -1
        best_val = 999
        for i, action in enumerate(actionList):
            if i == 0 or action[0] != "Pair":
                continue
            val = card_val.get(action[1], 99)
            if val < pair_ceiling and val < best_val:
                best_val = val
                best_idx = i
        if best_idx > 0:
            return best_idx
        for i, action in enumerate(actionList):
            if i == 0 or action[0] != "ThreeWithTwo":
                continue
            return i
        if pair_actionlist and card_val[pair_actionlist[0][0]] < pair_ceiling:
            idx = getindex("Pair", pair_actionlist, actionList)
            if idx > 0:
                return idx
        if threetwo_actionlist:
            idx = getindex("ThreeWithTwo", threetwo_actionlist, actionList)
            if idx > 0:
                return idx
        return -1

    def _is_solo_sprint(self, numofplayers, myPos):
        """GUA-034 END-M01: 队友已走完 → 1v2 solo 冲刺。"""
        return numofplayers[(myPos + 2) % 4] == 0

    def _gua034_is_wind_active(self, data):
        """接风首出：greaterPos==-1 或 curPos==-1。"""
        return data.get("greaterPos", -1) == -1 or data.get("curPos", -1) == -1

    def _gua035_solo_opponent_rests(self, numofplayers, myPos):
        """GUA-035 END-M02+-01: solo 下两家对手剩张（上家、下家）。"""
        return [numofplayers[(myPos + 1) % 4], numofplayers[(myPos + 3) % 4]]

    def _gua035_any_opponent_rest(self, opponent_rests, rest):
        return any(r == rest for r in opponent_rests)

    def _gua034_solo_active_pick(
        self, actionList, threetwo_actionlist, trips_actionlist, pair_actionlist,
        *, allow_threetwo=True, allow_pair=True,
    ):
        """GUA-034 END-M02 / GUA-035 END-M02+-02~04: 接风优先整手牌型。"""
        if allow_threetwo and threetwo_actionlist:
            idx = getindex("ThreeWithTwo", threetwo_actionlist, actionList)
            if idx > 0:
                self._dbg(f"GUA-034 END-M02 threetwo -> {idx}")
                return idx
        if trips_actionlist:
            idx = getindex("Trips", trips_actionlist, actionList)
            if idx > 0:
                self._dbg(f"GUA-034 END-M02 trips -> {idx}")
                return idx
        if allow_pair and pair_actionlist:
            idx = getindex("Pair", pair_actionlist, actionList)
            if idx > 0:
                self._dbg(f"GUA-034 END-M02 pair -> {idx}")
                return idx
        return -1

    def _gua035_solo_wind_pick(self, actionList, threetwo_actionlist, trips_actionlist, pair_actionlist, opponent_rests):
        """GUA-035: 接风首出 — 按对手剩张过滤，三带二无整手时 fallback。"""
        skip_tw = self._gua035_any_opponent_rest(opponent_rests, 5)
        skip_pair = self._gua035_any_opponent_rest(opponent_rests, 2)
        idx = self._gua034_solo_active_pick(
            actionList, threetwo_actionlist, trips_actionlist, pair_actionlist,
            allow_threetwo=not skip_tw, allow_pair=not skip_pair,
        )
        if idx <= 0 and skip_tw:
            self._dbg("GUA-035 END-M02+-04 threetwo fallback")
            idx = self._gua034_solo_active_pick(
                actionList, threetwo_actionlist, trips_actionlist, pair_actionlist,
                allow_threetwo=True, allow_pair=not skip_pair,
            )
        return idx, skip_tw, skip_pair, self._gua035_any_opponent_rest(opponent_rests, 1)

    def _gua034_solo_beat_single(self, single_actionList, card_val, curVal, rank_card, bomb_member):
        """GUA-034 END-M03: solo 下允许拆 trips 压对手小单。"""
        for tag, action in single_actionList:
            if card_val[action[1]] > curVal and rank_card not in action[2]:
                if action[2][0] in bomb_member:
                    continue
                self._dbg(f"GUA-034 END-M03 beat single -> {tag}")
                return tag
        return -1

    def _gua034_solo_beat_pair(
        self, pair_actionList, card_val, curVal, rank_card, bomb_member, straight_member,
    ):
        """GUA-034 END-M04: solo 下允许拆 trips 凑更大对。"""
        for tag, action in pair_actionList:
            if card_val[action[1]] > curVal and rank_card not in action[2]:
                if action[2][0] in bomb_member:
                    continue
                if is_inStraight(action, straight_member):
                    continue
                self._dbg(f"GUA-034 END-M04 beat pair -> {tag}")
                return tag
        return -1

    def _collect_bomb_action_list(self, actionList):
        bomb_actionList = []
        tag = 0
        for action in actionList[1:]:
            tag += 1
            if action[0] in ("Bomb", "StraightFlush"):
                bomb_actionList.append((tag, action))
        return bomb_actionList

    def _gua029_r4_allows_bomb(self, numofgreaterPos, numofmy, actionList):
        """GUA-029 R4：对手剩 4 张默认不炸（炸不打四），白名单例外。"""
        if numofgreaterPos != 4:
            return True
        for action in actionList[1:]:
            if action[0] in ("Bomb", "StraightFlush") and len(action[2]) == numofmy:
                return True
        non_pass = [a for a in actionList[1:] if a[0] != "PASS"]
        if non_pass and all(a[0] in ("Bomb", "StraightFlush") for a in non_pass):
            return True
        return False

    def _gua029_try_bomb(self, actionList, handcards, rank_card, card_val, myPos, greaterPos, numofplayers):
        """GUA-029：统一 choose_bomb，含 R4/R5 守卫。"""
        if greaterPos < 0 or greaterPos > 3:
            return -1
        if self._is_teammate_greater(myPos, greaterPos):
            return -1
        numofmy = numofplayers[myPos]
        numofgreaterPos = numofplayers[greaterPos]
        if not self._gua029_r4_allows_bomb(numofgreaterPos, numofmy, actionList):
            self._dbg("GUA-029 R4 block bomb (opp remain=4)")
            return -1
        sorted_cards, bomb_info = combine_handcards(handcards, rank_card[-1], card_val)
        bomb_actionList = self._collect_bomb_action_list(actionList)
        if not bomb_actionList:
            return -1
        bomb_actionList = self._gua032_filter_bomb_action_list(bomb_actionList, rank_card)
        if not bomb_actionList:
            self._dbg("GUA-032 CALC-M01 all bomb ranks filtered")
            return -1
        index = choose_bomb(bomb_actionList, handcards, sorted_cards, bomb_info, rank_card, card_val)
        if index != -1:
            self._dbg(f"GUA-029 choose_bomb -> {index}")
        return index

    def _gua029_passive_sprint_bomb(
        self, actionList, handcards, rank_card, card_val, myPos, greaterPos, numofplayers, beatAction,
    ):
        """GUA-029 R3：对手 ≤7 张且本分支已 PASS 时兜底出炸。"""
        if beatAction and beatAction[0] in ("Bomb", "StraightFlush"):
            return -1
        if greaterPos < 0 or greaterPos > 3:
            return -1
        if numofplayers[greaterPos] > 7:
            return -1
        return self._gua029_try_bomb(
            actionList, handcards, rank_card, card_val, myPos, greaterPos, numofplayers,
        )

    def _reset_state(self):
        self.history = {
            '0': {'send': [], 'remain': 27},
            '1': {'send': [], 'remain': 27},
            '2': {'send': [], 'remain': 27},
            '3': {'send': [], 'remain': 27},
        }
        self.remain_cards = {
            "S": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
            "H": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
            "C": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0],
            "D": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0],
        }
        self.remain_cards_classbynum = [8] * 13
        self.remain_cards_classbynum.append(2)
        self.remain_cards_classbynum.append(2)
        self.pass_num = 0
        self.my_pass_num = 0
        self.tribute_result = None
        self._player_bomb_mem = {
            str(i): {"has_bomb": False, "max_bomb_rank": 0} for i in range(4)
        }

    def _sync_remain_cards_classbynum(self):
        self.remain_cards_classbynum = sync_remain_cards_classbynum(self.remain_cards)

    def _rank_outside_count(self, rank_char):
        idx = CARD_INDEX.get(rank_char)
        if idx is None or idx >= 13:
            return 0
        return self.remain_cards_classbynum[idx]

    def _gua032_skip_passive_bomb_rank(self, action, rank_card):
        """CALC-M01: ≤3 cards of rank remain outside → passive skip that Bomb rank."""
        if action[0] != "Bomb":
            return False
        if rank_card in action[2]:
            return False
        bomb_rank = action[1]
        if bomb_rank not in CARD_INDEX:
            return False
        return self._rank_outside_count(bomb_rank) <= 3

    def _gua032_filter_bomb_action_list(self, bomb_actionList, rank_card):
        filtered = []
        for tag, action in bomb_actionList:
            if self._gua032_skip_passive_bomb_rank(action, rank_card):
                self._dbg(f"GUA-032 CALC-M01 skip bomb rank {action[1]} (outside≤3)")
                continue
            filtered.append((tag, action))
        return filtered

    def _gua032_straight_degraded(self, cards):
        """CALC-M03: 5/10 法则 — 关键张出尽则降权对应顺子。"""
        ranks = {str(c)[-1] for c in cards if len(str(c)) >= 2}
        if "T" in ranks and self.remain_cards_classbynum[9] == 0:
            return True
        if "5" in ranks and self.remain_cards_classbynum[4] == 0:
            return True
        return False

    def _refresh_bomb_memory(self, cur_pos, cur_action):
        """MEM-M02: track per-player bomb / straight-flush history."""
        if cur_pos is None or not cur_action or cur_action[0] not in ("Bomb", "StraightFlush"):
            return
        pos = str(cur_pos)
        mem = self._player_bomb_mem.setdefault(
            pos, {"has_bomb": False, "max_bomb_rank": 0},
        )
        mem["has_bomb"] = True
        rank_char = cur_action[1] if len(cur_action) > 1 else "2"
        rank_val = CARD_VALUE_S2V.get(rank_char, 0)
        if cur_action[0] == "StraightFlush":
            rank_val += 32
        if rank_val > mem["max_bomb_rank"]:
            mem["max_bomb_rank"] = rank_val

    def _update_play_state(self, data):
        curPos = data.get("curPos")
        curAction = self._ensure_list(data.get("curAction"))
        data["curAction"] = curAction  # ensure downstream sees list
        if (
            curPos is not None
            and curAction is not None
            and isinstance(curAction, list)
            and len(curAction) >= 1
            and curAction[0] != "PASS"
            and len(curAction) >= 3
            and isinstance(curAction[2], list)
        ):
            for card in curAction[2]:
                card_str = str(card)
                if card_str.upper() == "PASS" or len(card_str) < 2:
                    continue
                if card_str in ('B', 'R'):
                    ctype = 'S' if card_str == 'B' else 'H'
                    idx = 13
                else:
                    ctype = card_str[0]
                    rank_ch = card_str[-1]
                    if rank_ch not in CARD_INDEX:
                        continue
                    idx = CARD_INDEX[rank_ch]
                self.history[str(curPos)]["send"].append(card_str)
                self.history[str(curPos)]["remain"] -= 1
                self.remain_cards[ctype][idx] -= 1

        if curPos is not None:
            if curPos == self.player_id or curPos == (self.player_id + 2) % 4:
                if curAction and curAction[0] == "PASS":
                    self.pass_num += 1
                else:
                    self.pass_num = 0
            if curPos == self.player_id:
                if curAction and curAction[0] == "PASS":
                    self.my_pass_num += 1
                else:
                    self.my_pass_num = 0

        self._sync_remain_cards_classbynum()
        self._refresh_bomb_memory(curPos, curAction)

    def _sync_remain_from_public_info(self, data):
        """act 时用 publicInfo[].rest 对齐剩牌数（v1006 平台真源）。"""
        public_info = data.get("publicInfo")
        if not isinstance(public_info, list):
            return
        synced = 0
        for i, info in enumerate(public_info):
            if i > 3 or not isinstance(info, dict):
                continue
            rest = info.get("rest")
            if rest is None:
                continue
            try:
                n = int(rest)
            except (TypeError, ValueError):
                continue
            if 0 <= n <= 27:
                key = str(i)
                if key in self.history and self.history[key]["remain"] != n:
                    self._dbg(f"sync remain pos{i}: {self.history[key]['remain']} -> {n}")
                self.history[key]["remain"] = n
                synced += 1
        if synced:
            self._dbg(f"publicInfo.rest synced {synced} players")

    def on_message(self, data):
        stage = data.get("stage", "")
        msg_type = data.get("type", "")

        if stage in ("beginning", "episodeOver", "gameOver"):
            self._reset_state()

        # Normalize possibly stringified action fields (root cause of persistent PASS)
        if stage == "play":
            if "curAction" in data:
                data["curAction"] = self._ensure_list(data.get("curAction"))
            if "greaterAction" in data:
                data["greaterAction"] = self._ensure_list(data.get("greaterAction"))
            if "actionList" in data and isinstance(data["actionList"], list):
                data["actionList"] = [self._ensure_list(a) for a in data["actionList"]]

        if stage == "play" and msg_type == "notify":
            self._update_play_state(data)

        if stage == "play" and msg_type == "act":
            normalize_play_act_fields(data)
            self._sync_remain_from_public_info(data)
            resolved = resolve_effective_greater(
                cur_pos=data.get("curPos"),
                cur_action=data.get("curAction"),
                greater_pos=data.get("greaterPos", -1),
                greater_action=data.get("greaterAction"),
                public_info=data.get("publicInfo"),
                cur_rank=data.get("curRank", "2"),
            )
            if resolved["corrected"]:
                self._dbg(
                    "GUA-027 greater corrected "
                    f"src={resolved['source']} pos {data.get('greaterPos')}->{resolved['greater_pos']} "
                    f"act {data.get('greaterAction')}->{resolved['greater_action']}"
                )
            data["greaterPos"] = resolved["greater_pos"]
            data["greaterAction"] = resolved["greater_action"]
            data["_beat_action"] = resolved["beat_action"]

        if stage == "tribute" and msg_type == "notify":
            self.tribute_result = data.get("result")

        if "actionList" in data and data["actionList"]:
            action_list = data["actionList"]
            idx = self._rule_parse(data)
            idx = clamp_act_index(idx, action_list, data.get("indexRange"))
            chosen = action_list[idx] if 0 <= idx < len(action_list) else None
            self._dbg(f"on_message FINAL decision idx={idx} action={chosen}")
            return idx
        return -1

    def _rule_parse(self, data):
        action_list = data["actionList"]
        if len(action_list) == 1:
            self._dbg("only 1 action -> return 0 (PASS)")
            return 0

        stage = data.get("stage")
        mypos = self.player_id
        gpos = data.get("greaterPos", -1)
        cpos = data.get("curPos", -1)
        alen = len(action_list)
        self._dbg(f"ENTER _rule_parse | stage={stage} mypos={mypos} greaterPos={gpos} curPos={cpos} actionList_len={alen}")

        if stage == "play" and data.get("greaterPos") != mypos and data.get("curPos") != -1:
            numofplayers = [self.history['0']["remain"], self.history['1']["remain"],
                            self.history['2']["remain"], self.history['3']["remain"]]
            numofnext = numofplayers[(mypos + 1) % 4]
            if numofnext != 0:
                print("下家还有{}张牌".format(numofnext))
            else:
                numofpre = numofplayers[(mypos - 1) % 4]
                print("下家已完牌，上家还有{}张牌".format(numofpre))
            self._dbg("BRANCH: passive")
            idx = self._passive(data)
            self._dbg(f"passive -> return {idx}")
            return idx

        elif stage == "play" and (
            data.get("greaterPos") == -1
            or data.get("curPos") == -1
            or data.get("greaterPos") == mypos
        ):
            self._dbg("BRANCH: active (first-to-play or greaterPos==mypos)")
            numofplayers = [self.history['0']["remain"], self.history['1']["remain"],
                            self.history['2']["remain"], self.history['3']["remain"]]
            numofnext = numofplayers[(mypos + 1) % 4]
            if numofnext != 0:
                print("下家还有{}张牌".format(numofnext))
            else:
                numofpre = numofplayers[(mypos - 1) % 4]
            idx = self._active(data)
            self._dbg(f"active -> return {idx}")
            return idx

        elif stage == "back":
            self._dbg("BRANCH: back")
            return self._back_action(data)

        elif stage == "tribute":
            self._dbg("BRANCH: tribute")
            return self._tribute(data)

        elif stage == "play":
            self._dbg("BRANCH: fallback play (indexRange or active)")
            index_range = data.get("indexRange")
            if index_range is not None:
                self._dbg(f"fallback indexRange -> randint(0, {index_range})")
                return randint(0, index_range)
            idx = self._active(data)
            self._dbg(f"fallback active -> return {idx}")
            return idx

        self._dbg("FALLTHROUGH -> return 0")
        return 0

    def _passive(self, data):
        actionList = data["actionList"]
        handcards = data["handCards"]
        rank = data.get("curRank", "2")
        curAction = data.get("curAction") or ["PASS", "", "PASS"]
        greaterAction = data.get("greaterAction") or ["PASS", "", "PASS"]
        myPos = self.player_id
        greaterPos = data.get("greaterPos", -1)
        remaincards = self.remain_cards
        numofplayers = [self.history['0']["remain"], self.history['1']["remain"],
                        self.history['2']["remain"], self.history['3']["remain"]]
        pass_num = self.pass_num
        my_pass_num = self.my_pass_num
        remain_cards_classbynum = self.remain_cards_classbynum

        beatAction = data.get("_beat_action")
        if not beatAction:
            resolved = resolve_effective_greater(
                cur_pos=data.get("curPos"),
                cur_action=curAction,
                greater_pos=greaterPos,
                greater_action=greaterAction,
                public_info=data.get("publicInfo"),
                cur_rank=rank,
            )
            greaterPos = resolved["greater_pos"]
            greaterAction = resolved["greater_action"]
            beatAction = resolved["beat_action"]
        else:
            beatAction = self._ensure_list(beatAction)

        self._dbg(f"_passive ENTRY | curAction={curAction} greaterAction={greaterAction} "
                  f"beatAction={beatAction} numofplayers={numofplayers} pass_num={pass_num} "
                  f"my_pass_num={my_pass_num} greaterPos={greaterPos}")

        rank_card = 'H' + str(rank)
        restcards = rest_cards(handcards, remaincards, rank)

        card_val = CARD_VALUE_S2V.copy()
        card_val[rank_card[-1]] = 15

        actIndex = 0
        print(beatAction)
        numofmy = numofplayers[myPos]
        if numofmy <= 10:
            numofnext = numofplayers[(myPos + 1) % 4]
            actIndex = one_hand(numofmy, numofnext, actionList, myPos, greaterPos, 7,
                                restcards, card_val, rank_card)
            if actIndex != -1:
                self._dbg(f"one_hand early exit -> {actIndex}")
                return actIndex

        self._dbg(f"_passive dispatch | beatAction_type={beatAction[0] if beatAction else None} "
                  f"type={type(beatAction).__name__} [0]_repr={repr(beatAction[0]) if beatAction else None}")
        if beatAction[0] == "Single":
            actIndex = self._Single(actionList, beatAction, rank_card, handcards, numofplayers, restcards,
                                    card_val, myPos, greaterPos, pass_num, my_pass_num)
        elif beatAction[0] == "Pair":
            actIndex = self._Pair(actionList, beatAction, rank_card, handcards, numofplayers, restcards,
                                  card_val, myPos, greaterPos, pass_num, my_pass_num)
        elif beatAction[0] == "Trips":
            actIndex = self._Trips(actionList, beatAction, rank_card, handcards, numofplayers, restcards,
                                   card_val, myPos, greaterPos, pass_num, my_pass_num)
        elif beatAction[0] in ("ThreeWithTwo", "TripsPair"):
            actIndex = self._ThreeWithTwo(actionList, beatAction, rank_card, handcards, numofplayers, restcards,
                                          card_val, myPos, greaterPos, pass_num, my_pass_num)
        elif beatAction[0] == "ThreePair":
            actIndex = self._ThreePair(actionList, beatAction, rank_card, handcards, numofplayers, restcards,
                                       card_val, myPos, greaterPos, pass_num, my_pass_num)
        elif beatAction[0] == "TwoTrips":
            actIndex = self._TwoTrips(actionList, beatAction, rank_card, handcards, numofplayers, restcards,
                                      card_val, myPos, greaterPos, pass_num, my_pass_num)
        elif beatAction[0] == "Straight":
            actIndex = self._Straight(actionList, beatAction, rank_card, handcards, numofplayers,
                                      card_val, pass_num, my_pass_num, myPos, greaterPos)
        elif beatAction[0] == "Bomb" or beatAction[0] == "StraightFlush":
            actIndex = self._Bomb(actionList, beatAction, rank_card, handcards, numofplayers, restcards,
                                  card_val, myPos, greaterPos)

        if actIndex == 0:
            sprint_idx = self._gua029_passive_sprint_bomb(
                actionList, handcards, rank_card, card_val, myPos, greaterPos, numofplayers, beatAction,
            )
            if sprint_idx != -1:
                actIndex = sprint_idx
                self._dbg(f"GUA-029 R3 sprint bomb -> {actIndex}")

        self._dbg(f"_passive FINAL return actIndex={actIndex} (0 means PASS)")
        return actIndex

    def _Single(self, actionList, curAction, rank_card, handcards, numofplayers, rest_cards_list, card_val, myPos, greaterPos, pass_num, my_pass_num):
        self._dbg(f"_Single ENTRY | curAction={curAction} greaterPos={greaterPos} pass_num={pass_num} my_pass_num={my_pass_num}")
        numofnext = numofplayers[(myPos + 1) % 4]
        numofgreaterPos = numofplayers[greaterPos]
        numoffri = numofplayers[(myPos + 2) % 4]
        numofpre = numofplayers[(myPos - 1) % 4]
        self._dbg(f"_Single nums | numofnext={numofnext} numofgreaterPos={numofgreaterPos} numoffri={numoffri} numofpre={numofpre}")

        sorted_cards, bomb_info = combine_handcards(handcards, rank_card[-1], card_val)

        bomb_member = []
        pair_member = []
        trip_member = []
        single_member = sorted_cards["Single"]
        straight_member = []
        if len(sorted_cards["Straight"]) != 0:
            straight_member += sorted_cards["Straight"][0]
        if len(sorted_cards["StraightFlush"]) != 0:
            straight_member += sorted_cards["StraightFlush"][0]

        for pair in sorted_cards["Pair"]:
            pair_member += pair
        for trip in sorted_cards["Trips"]:
            trip_member += trip
        for bomb in sorted_cards["Bomb"]:
            bomb_member += bomb

        tag = 0
        single_actionList = []
        bomb_actionList = []
        for action in actionList[1:]:
            tag += 1
            if action[0] == 'Single':
                single_actionList.append((tag, action))
            else:
                bomb_actionList.append((tag, action))

        curVal = card_val[curAction[1]]

        max_val = card_val[rest_cards_list[-1][0][-1]]

        self._dbg(f"_Single VALUES | curVal={curVal} max_val_from_remain={max_val} "
                  f"len(single_actionList)={len(single_actionList)} len(bomb_actionList)={len(bomb_actionList)} "
                  f"single_member_top5={[c[1] for c in single_member[:5]] if single_member else []}")

        if numofnext == 0:
            numofnext = numofplayers[(myPos - 1) % 4]

        if numofnext <= 4 or (numofpre <= 3 and numofpre >= 1):
            if (myPos + 2) % 4 == greaterPos and curVal >= max_val:
                self._dbg("_Single early teammate protect (curVal >= max_val) -> 0")
                return 0
            if (myPos + 2) % 4 == greaterPos and curVal >= 15 and numofnext != 1:
                self._dbg("_Single early teammate protect (curVal>=15) -> 0")
                return 0

            for action in single_actionList:
                Index = action[0]
                action = action[1]
                if card_val[action[1]] >= max_val and action[2][0] in single_member and rank_card not in action[2]:
                    return Index

            for action in single_actionList:
                Index = action[0]
                action = action[1]
                if card_val[action[1]] >= max_val and action[2][0] not in bomb_member and rank_card not in action[2]:
                    if is_inStraight(action, straight_member):
                        continue
                    return Index

            index = choose_bomb(bomb_actionList, handcards, sorted_cards, bomb_info, rank_card, card_val)
            if index != -1:
                return index

            for action in single_actionList:
                Index = action[0]
                action = action[1]
                if card_val[action[1]] >= max_val - 2 and action[2][0] not in bomb_member and rank_card not in action[2]:
                    if is_inStraight(action, straight_member):
                        continue
                    return Index

            for action in single_actionList:
                Index = action[0]
                action = action[1]
                if rank_card in action[2] and (len(sorted_cards["Pair"]) < 3 or numofnext == 1):
                    return Index

        def normal(single_actionList, single_member, rank_card):
            for action in single_actionList:
                Index = action[0]
                action = action[1]
                if (action[2][0] in single_member or card_val[action[1]] >= 15) and rank_card not in action[2]:
                    return Index
            return -1

        def special(single_actionList, bomb_member, straight_member, rank_card):
            for action in single_actionList[::-1]:
                Index = action[0]
                action = action[1]
                if action[2][0] not in bomb_member and rank_card not in action[2]:
                    if is_inStraight(action, straight_member):
                        continue
                    return Index
            return -1

        if (myPos + 2) % 4 == greaterPos:
            if curVal >= 14 or curVal >= max_val - 2:
                return 0
            elif numoffri <= 4:
                index = normal(single_actionList, single_member, rank_card)
                if index == -1:
                    return 0
                if curVal <= 10:
                    return index
                else:
                    if card_val[actionList[index][1]] == curVal + 1:
                        return index
            else:
                index = normal(single_actionList, single_member, rank_card)
                if index != -1:
                    return index
                else:
                    return 0
        else:
            if self._is_solo_sprint(numofplayers, myPos):
                idx = self._gua034_solo_beat_single(
                    single_actionList, card_val, curVal, rank_card, bomb_member,
                )
                if idx != -1:
                    return idx
                return 0
            index = normal(single_actionList, single_member, rank_card)
            if index != -1:
                return index
            else:
                if pass_num >= 5 or my_pass_num >= 3:
                    index = special(single_actionList, bomb_member, straight_member, rank_card)
                    if index != -1:
                        return index
                cur_bomb_num = cal_bomb_num(sorted_cards, handcards, rank_card)
                if curVal >= max_val and numofgreaterPos >= 15 and cur_bomb_num > 1:
                    p = random()
                    index = choose_bomb(bomb_actionList, handcards, sorted_cards, bomb_info, rank_card, card_val)
                    if p > 0.5:
                        if index != -1:
                            return index
                elif ((curVal >= 15 or curVal >= max_val - 2) and numofgreaterPos <= 15) or pass_num >= 7 or my_pass_num >= 5:
                    index = choose_bomb(bomb_actionList, handcards, sorted_cards, bomb_info, rank_card, card_val)
                    if index != -1:
                        return index
                    else:
                        self._dbg("_Single bomb not chosen under high pass_num -> 0")
                        return 0

        self._dbg("_Single reached final return 0 (no branch taken) - possible reasons: no playable single >= required value, no good bomb, strict teammate protection, or pass_num thresholds")
        self._dbg(f"_Single FINAL STATE | curVal={curVal} max_val={max_val} pass_num={pass_num} my_pass_num={my_pass_num} numofgreaterPos={numofgreaterPos} numofnext={numofnext}")
        return 0

    def _Pair(self, actionList, curAction, rank_card, handcards, numofplayers, rest_cards_list, card_val, myPos, greaterPos, pass_num, my_pass_num):
        self._dbg(f"_Pair ENTRY | curAction={curAction} greaterPos={greaterPos} pass_num={pass_num} my_pass_num={my_pass_num}")
        numofnext = numofplayers[(myPos + 1) % 4]
        numofgreaterPos = numofplayers[greaterPos]
        numoffri = numofplayers[(myPos + 2) % 4]
        numofpre = numofplayers[(myPos - 1) % 4]
        self._dbg(f"_Pair nums | numofnext={numofnext} numofgreaterPos={numofgreaterPos}")
        sorted_cards, bomb_info = combine_handcards(handcards, rank_card[-1], card_val)

        bomb_member = []
        pair_member = []
        trip_member = []
        single_member = sorted_cards["Single"]
        straight_member = []
        if len(sorted_cards["Straight"]) != 0:
            straight_member += sorted_cards["Straight"][0]
        if len(sorted_cards["StraightFlush"]) != 0:
            straight_member += sorted_cards["StraightFlush"][0]

        for pair in sorted_cards["Pair"]:
            pair_member += pair
        for trip in sorted_cards["Trips"]:
            trip_member += trip
        for bomb in sorted_cards["Bomb"]:
            bomb_member += bomb

        pair_actionList = []
        bomb_actionList = []
        tag = 0
        for action in actionList[1:]:
            tag += 1
            if action[0] == 'Pair':
                pair_actionList.append((tag, action))
            else:
                bomb_actionList.append((tag, action))

        curVal = card_val[curAction[1]]
        rest_cards_list = rest_cards_list[::-1]
        max_val = 0
        for cards in rest_cards_list:
            if len(cards) >= 2:
                max_val = card_val[cards[0][-1]]
                break
        if numofnext == 0:
            numofnext = numofplayers[(myPos - 1) % 4]

        if numofnext <= 4 or (numofpre <= 4 and numofpre >= 1):
            if (myPos + 2) % 4 == greaterPos and curVal >= max_val:
                return 0
            if (myPos + 2) % 4 == greaterPos and curVal >= 12 and numofnext != 2:
                return 0

            for action in pair_actionList:
                Index = action[0]
                action = action[1]
                if card_val[action[1]] >= max_val and action[2][0] in pair_member and rank_card not in action[2]:
                    return Index

            for action in pair_actionList:
                Index = action[0]
                action = action[1]
                if card_val[action[1]] >= max_val and action[2][0] not in bomb_member and rank_card not in action[2]:
                    if is_inStraight(action, straight_member):
                        continue
                    return Index

            index = choose_bomb(bomb_actionList, handcards, sorted_cards, bomb_info, rank_card, card_val)
            if index != -1:
                return index

            for action in pair_actionList[::-1]:
                Index = action[0]
                action = action[1]
                if card_val[action[1]] >= max_val - 2 and action[2][0] not in bomb_member and rank_card not in action[2]:
                    if is_inStraight(action, straight_member):
                        continue
                    return Index

            max_match = -1
            max_match_index = -1
            for action in pair_actionList:
                index = action[0]
                action = action[1]
                if rank_card in action[2] and card_val[action[1]] > max_match and action[2][0] not in bomb_member:
                    if is_inStraight(action, straight_member):
                        continue
                    max_match = card_val[action[1]]
                    max_match_index = index
            if max_match_index != -1 and max_match >= max_val - 2:
                return max_match_index

        def normal(pair_actionList, pair_member, rank_card):
            for action in pair_actionList:
                Index = action[0]
                action = action[1]
                if (action[2][0] in pair_member or action[-1] == rank_card[-1]) and rank_card not in action[2]:
                    return Index
            return -1

        def special(pair_actionList, bomb_member, straight_member, rank_card):
            for action in pair_actionList[::-1]:
                Index = action[0]
                action = action[1]
                if action[2][0] not in bomb_member and rank_card not in action[2]:
                    if is_inStraight(action, straight_member):
                        continue
                    return Index
            return -1

        if (myPos + 2) % 4 == greaterPos:
            if curVal >= 13 or curVal >= max_val - 2:
                return 0
            elif numoffri <= 4:
                index = normal(pair_actionList, pair_member, rank_card)
                if index == -1:
                    return 0
                if curVal <= 10:
                    return index
                else:
                    if card_val[actionList[index][1]] == curVal + 1:
                        return index
            else:
                index = normal(pair_actionList, pair_member, rank_card)
                if index != -1:
                    return index
                else:
                    return 0
        else:
            if self._is_solo_sprint(numofplayers, myPos):
                idx = self._gua034_solo_beat_pair(
                    pair_actionList, card_val, curVal, rank_card, bomb_member, straight_member,
                )
                if idx != -1:
                    return idx
                return 0
            index = normal(pair_actionList, pair_member, rank_card)
            if index != -1:
                return index
            else:
                if pass_num >= 5 or my_pass_num >= 3:
                    index = special(pair_actionList, bomb_member, straight_member, rank_card)
                    if index != -1:
                        return index
                cur_bomb_num = cal_bomb_num(sorted_cards, handcards, rank_card)
                if curVal >= max_val and numofgreaterPos >= 15 and cur_bomb_num > 1:
                    p = random()
                    index = choose_bomb(bomb_actionList, handcards, sorted_cards, bomb_info, rank_card, card_val)
                    if p > 0.5:
                        if index != -1:
                            return index
                elif ((curVal >= 14 or curVal >= max_val - 2) and numofgreaterPos <= 15) or pass_num >= 6 or my_pass_num >= 5:
                    index = choose_bomb(bomb_actionList, handcards, sorted_cards, bomb_info, rank_card, card_val)
                    if index != -1:
                        return index
                    else:
                        return 0

        return 0

    def _ThreeWithTwo(self, actionList, curAction, rank_card, handcards, numofplayers, rest_cards_list, card_val, myPos, greaterPos, pass_num, my_pass_num):
        numofnext = numofplayers[(myPos + 1) % 4]
        numofgreaterPos = numofplayers[greaterPos]
        numoffri = numofplayers[(myPos + 2) % 4]
        numofpre = numofplayers[(myPos - 1) % 4]

        sorted_cards, bomb_info = combine_handcards(handcards, rank_card[-1], card_val)

        bomb_member = []
        pair_member = []
        trip_member = []
        single_member = sorted_cards["Single"]
        straight_member = []
        if len(sorted_cards["Straight"]) != 0:
            straight_member += sorted_cards["Straight"][0]
        if len(sorted_cards["StraightFlush"]) != 0:
            straight_member += sorted_cards["StraightFlush"][0]

        for pair in sorted_cards["Pair"]:
            pair_member += pair
        for trip in sorted_cards["Trips"]:
            trip_member += trip
        for bomb in sorted_cards["Bomb"]:
            bomb_member += bomb

        three2_actionList = []
        bomb_actionList = []
        tag = 0

        for action in actionList[1:]:
            tag += 1
            if action[0] in ('ThreeWithTwo', 'TripsPair'):
                three2_actionList.append((tag, action))
            else:
                bomb_actionList.append((tag, action))

        curVal = card_val[curAction[1]]
        max_val = 0
        for cards in rest_cards_list[::-1]:
            if len(cards) >= 3:
                max_val = card_val[cards[0][-1]]
                break

        if numofnext == 0:
            numofnext = numofplayers[(myPos - 1) % 4]

        if numofnext <= 7 or (numofpre <= 7 and numofpre >= 1):
            if (myPos + 2) % 4 == greaterPos and curVal >= max_val:
                return 0
            if (myPos + 2) % 4 == greaterPos and curVal >= 11 and numofnext != 5:
                return 0

            index = self._pick_three_with_two(
                three2_actionList,
                trip_member,
                pair_member,
                bomb_member,
                rank_card,
                card_val,
                allow_split_trips=(numofnext <= 6),
                prefer_low=False,
            )
            if index != -1:
                return index

            index = choose_bomb(bomb_actionList, handcards, sorted_cards, bomb_info, rank_card, card_val)
            if index != -1:
                return index

        def normal(three2_actionList, trip_member, pair_member, rank_card):
            return self._pick_three_with_two(
                three2_actionList,
                trip_member,
                pair_member,
                bomb_member,
                rank_card,
                card_val,
                allow_split_trips=False,
                prefer_low=True,
            )

        if (myPos + 2) % 4 == greaterPos:
            if curVal >= 14 or curVal >= max_val - 2:
                return 0
            elif numoffri <= 5:
                index = normal(three2_actionList, trip_member, pair_member, rank_card)
                if index == -1:
                    return 0
                if curVal <= 10:
                    return index
                else:
                    if card_val[actionList[index][1]] == curVal + 1:
                        return index
            else:
                index = normal(three2_actionList, trip_member, pair_member, rank_card)
                if index != -1:
                    return index
                else:
                    return 0
        else:
            index = normal(three2_actionList, trip_member, pair_member, rank_card)
            if index != -1:
                return index
            else:
                if curVal >= max_val and numofgreaterPos >= 15:
                    p = random()
                    if p > 0.5:
                        index = choose_bomb(bomb_actionList, handcards, sorted_cards, bomb_info, rank_card, card_val)
                        if index != -1:
                            return index
                if ((curVal >= 12 or curVal >= max_val - 2) and numofgreaterPos <= 15) or pass_num >= 5 or my_pass_num >= 3:
                    index = choose_bomb(bomb_actionList, handcards, sorted_cards, bomb_info, rank_card, card_val)
                    if index != -1:
                        return index
                    else:
                        self._dbg("_ThreeWithTwo high-pass bomb not taken -> 0")
                        return 0
        self._dbg("_ThreeWithTwo reached final return 0")
        return 0

    def _Trips(self, actionList, curAction, rank_card, handcards, numofplayers, rest_cards_list, card_val, myPos, greaterPos, pass_num, my_pass_num):
        numofnext = numofplayers[(myPos + 1) % 4]
        numofgreaterPos = numofplayers[greaterPos]
        numoffri = numofplayers[(myPos + 2) % 4]
        numofpre = numofplayers[(myPos - 1) % 4]
        numofmy = numofplayers[myPos]
        if self._gua031_passive_teammate_yield(myPos, greaterPos, numofmy):
            self._dbg("GUA-031 P-F02 _Trips teammate yield -> 0")
            return 0

        sorted_cards, bomb_info = combine_handcards(handcards, rank_card[-1], card_val)

        bomb_member = []
        pair_member = []
        trip_member = []
        single_member = sorted_cards["Single"]
        straight_member = []
        if len(sorted_cards["Straight"]) != 0:
            straight_member += sorted_cards["Straight"][0]
        if len(sorted_cards["StraightFlush"]) != 0:
            straight_member += sorted_cards["StraightFlush"][0]

        for pair in sorted_cards["Pair"]:
            pair_member += pair
        for trip in sorted_cards["Trips"]:
            trip_member += trip
        for bomb in sorted_cards["Bomb"]:
            bomb_member += bomb

        trip_actionList = []
        bomb_actionList = []
        tag = 0
        for action in actionList[1:]:
            tag += 1
            if action[0] == 'Trips':
                trip_actionList.append((tag, action))
            else:
                bomb_actionList.append((tag, action))

        curVal = card_val[curAction[1]]
        rest_cards_list = rest_cards_list[::-1]
        max_val = 0
        for cards in rest_cards_list:
            if len(cards) >= 3:
                max_val = card_val[cards[0][-1]]
                break

        if numofnext == 0:
            numofnext = numofplayers[(myPos - 1) % 4]

        if numofnext <= 6 or (numofpre <= 5 and numofpre >= 1):
            if (myPos + 2) % 4 == greaterPos and curVal >= max_val:
                return 0
            if (myPos + 2) % 4 == greaterPos and curVal >= 12 and numofnext != 3:
                return 0

            for action in trip_actionList:
                Index = action[0]
                action = action[1]
                if card_val[action[1]] >= max_val and action[2][0] in trip_member and action[2] and rank_card not in action[2]:
                    return Index

            index = choose_bomb(bomb_actionList, handcards, sorted_cards, bomb_info, rank_card, card_val)
            if index != -1:
                return index

            for action in trip_actionList[::-1]:
                Index = action[0]
                action = action[1]
                if card_val[action[1]] >= max_val - 2 and action[2][0] in trip_member and rank_card not in action[2]:
                    if is_inStraight(action, straight_member):
                        continue
                    return Index
            max_match = -1
            max_match_index = -1
            for action in trip_actionList:
                index = action[0]
                action = action[1]
                if rank_card in action[2] and card_val[action[1]] > max_match and action[2][0] not in bomb_member:
                    if is_inStraight(action, straight_member):
                        continue
                    max_match = card_val[action[1]]
                    max_match_index = index
            if max_match_index != -1:
                return max_match_index

        def normal(trip_actionList, trip_member, rank_card):
            for action in trip_actionList:
                Index = action[0]
                action = action[1]
                if action[2][0] in trip_member and rank_card not in action[2]:
                    return Index
            return -1

        if (myPos + 2) % 4 == greaterPos:
            if curVal >= 13 or curVal >= max_val - 2:
                return 0
            elif numoffri <= 4:
                index = normal(trip_actionList, trip_member, rank_card)
                if index == -1:
                    return 0
                if curVal <= 10:
                    return index
                else:
                    if card_val[actionList[index][1]] == curVal + 1:
                        return index
            else:
                index = normal(trip_actionList, trip_member, rank_card)
                if index != -1:
                    return index
                else:
                    return 0
        else:
            index = normal(trip_actionList, trip_member, rank_card)
            if index != -1:
                return index
            else:
                if curVal >= max_val and numofgreaterPos >= 15:
                    p = random()
                    if p > 0.5:
                        index = choose_bomb(bomb_actionList, handcards, sorted_cards, bomb_info, rank_card, card_val)
                        if index != -1:
                            return index
                if ((curVal >= 12 or curVal >= max_val - 2) and numofgreaterPos <= 15) or pass_num >= 5 or my_pass_num >= 3:
                    index = choose_bomb(bomb_actionList, handcards, sorted_cards, bomb_info, rank_card, card_val)
                    if index != -1:
                        return index

        return 0

    def _ThreePair(self, actionList, curAction, rank_card, handcards, numofplayers, rest_cards_list, card_val, myPos, greaterPos, pass_num, my_pass_num):
        numofnext = numofplayers[(myPos + 1) % 4]
        numofgreaterPos = numofplayers[greaterPos]
        numoffri = numofplayers[(myPos + 2) % 4]
        numofpre = numofplayers[(myPos - 1) % 4]
        numofmy = numofplayers[myPos]
        if self._gua031_passive_teammate_yield(myPos, greaterPos, numofmy):
            self._dbg("GUA-031 P-F02 _ThreePair teammate yield -> 0")
            return 0
        sorted_cards, bomb_info = combine_handcards(handcards, rank_card[-1], card_val)

        card_origin = CARD_ORIGIN.copy()
        card_val['A'] = 1
        card_val[rank_card[-1]] = card_origin[rank_card[-1]]

        bomb_member = []
        pair_member = []
        trip_member = []
        single_member = sorted_cards["Single"]
        straight_member = []
        if len(sorted_cards["Straight"]) != 0:
            straight_member += sorted_cards["Straight"][0]
        if len(sorted_cards["StraightFlush"]) != 0:
            straight_member += sorted_cards["StraightFlush"][0]

        for pair in sorted_cards["Pair"]:
            pair_member += pair
        for trip in sorted_cards["Trips"]:
            trip_member += trip
        for bomb in sorted_cards["Bomb"]:
            bomb_member += bomb

        pair3_actionList = []
        bomb_actionList = []

        tag = 0
        for action in actionList[1:]:
            tag += 1
            if (action[0] == 'ThreePair'):
                pair3_actionList.append((tag, action))
            else:
                bomb_actionList.append((tag, action))

        curVal = card_val[curAction[1]]
        max_val = 0
        val_list = []
        for cards in rest_cards_list:
            if len(cards) >= 2:
                val_list.append(card_val[cards[0][-1]])
        val_list = sorted(val_list)

        for i in range(0, len(val_list)):
            if i >= len(val_list) - 2:
                break
            if (val_list[i] + 1 == val_list[i + 1] and val_list[i] + 2 == val_list[i + 2]):
                max_val = max(max_val, val_list[i])

        if len(val_list) >= 3 and (val_list[0] == 1 and val_list[-2] == 12 and val_list[-1] == 13):
            max_val = 12

        def normal(pair3_actionList, pair_member, rank_card):
            for action in pair3_actionList:
                index = action[0]
                action = action[1]
                first = action[2][0]
                mid = action[2][2]
                last = action[2][4]
                if first in pair_member and mid in pair_member and last in pair_member and rank_card not in action[2]:
                    return index
            return -1

        def special(pair3_actionList, trip_member, rank_card):
            for action in pair3_actionList:
                index = action[0]
                action = action[1]
                first = action[2][0]
                mid = action[2][2]
                last = action[2][4]
                if rank_card in action[2]:
                    continue
                if first in pair_member and mid in pair_member and last in trip_member:
                    return index
                if first in pair_member and mid in trip_member and last in pair_member:
                    return index
                if first in trip_member and mid in pair_member and last in pair_member:
                    return index
            return -1

        def match_rank_card(pair3_actionList, rank_card, pair_member):
            for action in pair3_actionList:
                index = action[0]
                action = action[1]
                first = action[2][1]
                mid = action[2][3]
                last = action[2][5]
                if first == rank_card and mid in pair_member and last in pair_member:
                    return index
                if first in pair_member and mid == rank_card and last in pair_member:
                    return index
                if first in pair_member and mid == rank_card and last in pair_member:
                    return index
            return -1

        if (myPos + 2) % 4 == greaterPos:
            if curVal >= 10 or curVal >= max_val - 2:
                return 0
            elif numoffri <= 4:
                index = normal(pair3_actionList, pair_member, rank_card)
                if index == -1:
                    return 0
                if curVal <= 7:
                    return index
                else:
                    if card_val[actionList[index][1]] == curVal + 1:
                        return index
            else:
                index = normal(pair3_actionList, pair_member, rank_card)
                if index != -1:
                    return index
                else:
                    return 0
        else:
            index = normal(pair3_actionList, pair_member, rank_card)
            if index != -1:
                return index
            else:
                index = special(pair3_actionList, trip_member, rank_card)
                if index != -1:
                    return index
                if len(trip_member) == 0 and rank_card in handcards:
                    index = match_rank_card(pair3_actionList, rank_card, pair_member)
                    if index != -1:
                        return index
                if curVal >= max_val and numofgreaterPos >= 15:
                    index = choose_bomb(bomb_actionList, handcards, sorted_cards, bomb_info, rank_card, card_val)
                    if index != -1:
                        return index
                elif ((curVal >= 10 or curVal >= max_val - 2) and numofgreaterPos <= 15) or pass_num >= 5 or my_pass_num >= 3:
                    index = choose_bomb(bomb_actionList, handcards, sorted_cards, bomb_info, rank_card, card_val)
                    if index != -1:
                        return index
                    else:
                        return 0

        return 0

    def _Straight(self, actionList, curAction, rank_card, handcards, numofplayers, card_val, pass_num, my_pass_num, myPos, greaterPos):
        numofnext = numofplayers[(myPos + 1) % 4]
        numofpre = numofplayers[(myPos - 1) % 4]
        numofmy = numofplayers[myPos]
        if self._gua031_passive_teammate_yield(myPos, greaterPos, numofmy):
            self._dbg("GUA-031 P-F02 _Straight teammate yield -> 0")
            return 0
        if numofnext == 0:
            numofnext = numofplayers[(myPos - 1) % 4]

        sorted_cards, bomb_info = combine_handcards(handcards, rank_card[-1], card_val)

        card_origin = CARD_ORIGIN.copy()
        card_val['A'] = 1
        card_val[rank_card[-1]] = card_origin[rank_card[-1]]

        curVal = card_val[curAction[1]]

        bomb_member = []
        pair_member = []
        trip_member = []
        single_member = sorted_cards["Single"]
        straight_member = []
        if len(sorted_cards["Straight"]) != 0:
            straight_member += sorted_cards["Straight"][0]
        if len(sorted_cards["StraightFlush"]) != 0:
            straight_member += sorted_cards["StraightFlush"][0]

        for pair in sorted_cards["Pair"]:
            pair_member += pair
        for trip in sorted_cards["Trips"]:
            trip_member += trip
        for bomb in sorted_cards["Bomb"]:
            bomb_member += bomb

        straight_actionList = []
        bomb_actionList = []
        tag = 0
        for action in actionList[1:]:
            tag += 1
            if action[0] == 'Straight':
                straight_actionList.append((tag, action))
            else:
                bomb_actionList.append((tag, action))

        if len(sorted_cards["Straight"]) > 0:
            curStraight = sorted_cards["Straight"][0][0][-1]
            for action in straight_actionList:
                Index = action[0]
                action = action[1]
                if self._gua032_straight_degraded(action[2]):
                    self._dbg("GUA-032 CALC-M03 skip straight (5/10 depleted)")
                    continue
                if curStraight == action[-1] and rank_card not in action[2]:
                    if (myPos + 2) % 4 == greaterPos:
                        if curVal <= 7 or card_val[curStraight] - curVal <= 2:
                            return Index
                    else:
                        return Index
        elif (myPos + 2) != greaterPos:
            for action in straight_actionList:
                Index = action[0]
                action = action[1]
                if self._gua032_straight_degraded(action[2]):
                    self._dbg("GUA-032 CALC-M03 skip straight (5/10 depleted)")
                    continue
                if rank_card in action[2] and len(trip_member) == 0:
                    if len(set(action[2]).intersection(set(bomb_member))) != 0:
                        continue
                    if is_inStraight(action, straight_member):
                        continue
                    new_handcards = []
                    for card in handcards:
                        if card not in action[2]:
                            new_handcards.append(card)

                    new_card_val = copy.deepcopy(card_val)
                    new_card_val['A'] = 14
                    new_card_val[rank_card[-1]] = 15
                    originSinglenum = len(single_member)
                    new_sorted_cards, _ = combine_handcards(new_handcards, rank_card, new_card_val)
                    curSinglenum = len(new_sorted_cards["Single"])
                    if curSinglenum <= originSinglenum:
                        return Index

            if (numofnext <= 15 or curVal >= 9) or numofnext <= 10 or pass_num >= 5 or my_pass_num >= 3 or numofpre <= 5:
                index = choose_bomb(bomb_actionList, handcards, sorted_cards, bomb_info, rank_card, card_val)
                if index != -1:
                    return index

        return 0

    def _TwoTrips(self, actionList, curAction, rank_card, handcards, numofplayers, rest_cards_list, card_val, myPos, greaterPos, pass_num, my_pass_num):
        numofnext = numofplayers[(myPos + 1) % 4]
        numofgreaterPos = numofplayers[greaterPos]
        numoffri = numofplayers[(myPos + 2) % 4]
        numofmy = numofplayers[myPos]
        if self._gua031_passive_teammate_yield(myPos, greaterPos, numofmy):
            self._dbg("GUA-031 P-F02 _TwoTrips teammate yield -> 0")
            return 0

        sorted_cards, bomb_info = combine_handcards(handcards, rank_card[-1], card_val)

        card_origin = CARD_ORIGIN.copy()
        card_val['A'] = 1
        card_val[rank_card[-1]] = card_origin[rank_card[-1]]

        bomb_member = []
        pair_member = []
        trip_member = []
        single_member = sorted_cards["Single"]
        straight_member = []
        if len(sorted_cards["Straight"]) != 0:
            straight_member += sorted_cards["Straight"][0]
        if len(sorted_cards["StraightFlush"]) != 0:
            straight_member += sorted_cards["StraightFlush"][0]

        for pair in sorted_cards["Pair"]:
            pair_member += pair
        for trip in sorted_cards["Trips"]:
            trip_member += trip
        for bomb in sorted_cards["Bomb"]:
            bomb_member += bomb

        twoTripsList = []
        bomb_actionList = []
        tag = 0

        for action in actionList[1:]:
            tag += 1
            if (action[0] == "TwoTrips"):
                twoTripsList.append((tag, action))
            else:
                bomb_actionList.append((tag, action))

        curVal = card_val[curAction[1]]
        max_val = 0
        val_list = []
        for cards in rest_cards_list:
            if len(cards) >= 3:
                val_list.append(card_val[cards[0][-1]])
        val_list = sorted(val_list)
        for i in range(0, len(val_list)):
            if (i >= len(val_list) - 1):
                break
            if (val_list[i] + 1 == val_list[i + 1]):
                max_val = max(max_val, val_list[i])
        if len(val_list) >= 2 and val_list[0] == 1 and val_list[-1] == 13:
            max_val = 13

        def normal(twoTripsList, trip_member, rank_card):
            for action in twoTripsList:
                index = action[0]
                action = action[1]
                first = action[2][0]
                last = action[2][3]
                if first in trip_member and last in trip_member and rank_card not in action[2]:
                    return index
            return -1

        if (myPos + 2) % 4 == greaterPos:
            if curVal >= 10 or curVal >= max_val - 2:
                return 0
            elif numoffri <= 4:
                index = normal(twoTripsList, trip_member, rank_card)
                if index == -1:
                    return 0
                if curVal <= 10:
                    return index
                else:
                    if card_val[actionList[index][1]] == curVal + 1:
                        return index
            else:
                index = normal(twoTripsList, trip_member, rank_card)
                if index != -1:
                    return index
                else:
                    return 0
        else:
            index = normal(twoTripsList, trip_member, rank_card)
            if index != -1:
                return index
            else:
                if curVal >= max_val and numofgreaterPos >= 15:
                    p = random()
                    if p > 0.5:
                        index = choose_bomb(bomb_actionList, handcards, sorted_cards, bomb_info, rank_card, card_val)
                        if index != -1:
                            return index
                if ((curVal >= 10 or curVal >= max_val - 2) and numofgreaterPos <= 15) or pass_num >= 5 or my_pass_num >= 3:
                    index = choose_bomb(bomb_actionList, handcards, sorted_cards, bomb_info, rank_card, card_val)
                    if index != -1:
                        return index
                    else:
                        return 0
        return 0

    def _Bomb(self, actionList, curAction, rank_card, handcards, numofplayers, rest_cards_list, card_val, myPos, greaterPos):
        """GUA-029 R2：对 Bomb/SF 必回炸（最小够用）。"""
        if self._is_teammate_greater(myPos, greaterPos):
            return 0
        index = self._gua029_try_bomb(
            actionList, handcards, rank_card, card_val, myPos, greaterPos, numofplayers,
        )
        if index != -1:
            return index
        return 0

    def _active(self, data):
        self._dbg("ENTER _active (first-to-play or own greater)")
        actionList = data["actionList"]
        handcards = data["handCards"]
        rank = data.get("curRank", "2")
        numofplayers = [self.history['0']["remain"], self.history['1']["remain"],
                        self.history['2']["remain"], self.history['3']["remain"]]
        mypos = self.player_id
        remaincards = self.remain_cards

        restcards = rest_cards(handcards, remaincards, rank)
        rank_card = 'H' + rank
        card_val = CARD_VALUE_S2V.copy()
        card_val[rank] = 15
        numofnext = numofplayers[(mypos + 1) % 4]
        if numofnext == 0:
            numofnext = numofplayers[(mypos - 1) % 4]

        numofmy = numofplayers[mypos]
        greater_pos = data.get("greaterPos", mypos)
        if greater_pos is None or greater_pos < 0:
            greater_pos = mypos

        if numofmy <= 10:
            oh = one_hand(
                numofmy, numofnext, actionList, mypos, greater_pos, 7, restcards, card_val, rank_card,
            )
            if oh != -1:
                self._dbg(f"GUA-029 R6 one_hand active -> {oh}")
                return oh
            for i, action in enumerate(actionList):
                if i == 0:
                    continue
                if action[0] in ("Bomb", "StraightFlush") and len(action[2]) == numofmy:
                    self._dbg(f"GUA-029 R6 bomb finish active -> {i}")
                    return i

        cur = [9, 10, 9, 8, 10, 10, 2]

        card_val2 = CARD_VALUE_S2V2.copy()

        sorted_cards, single_actionlist, pair_actionlist, trips_actionlist, threepair_actionlist, threetwo_actionlist, twotrips_actionlist, straight_actionlist = self._get_list(
            handcards, rank)
        print(len(single_actionlist), len(pair_actionlist), len(trips_actionlist), len(threetwo_actionlist),
              len(threepair_actionlist), len(twotrips_actionlist), len(straight_actionlist))

        max_val = card_val[restcards[-1][0][-1]]

        numoffri = numofplayers[(mypos + 2) % 4]
        single_for_play = self._gua031_filter_singles_for_next1(
            single_actionlist, card_val, numofnext,
        )

        if numoffri == 1:
            idx = self._gua031_active_min_single(actionList, single_actionlist, card_val)
            if idx > 0:
                self._dbg(f"GUA-031 P02 min single -> {idx}")
                return idx

        if numoffri == 5:
            idx = self._gua031_active_feed_five(
                actionList, pair_actionlist, threetwo_actionlist, card_val, cur,
            )
            if idx > 0:
                self._dbg(f"GUA-031 P04 feed pair/tw2 -> {idx}")
                return idx

        solo = self._is_solo_sprint(numofplayers, mypos)
        solo_wind = solo and numofmy <= 12 and self._gua034_is_wind_active(data)

        for i in actionList:
            if len(handcards) == len(i[2]):
                return actionList.index(i)

        if solo_wind:
            opponent_rests = self._gua035_solo_opponent_rests(numofplayers, mypos)
            idx, skip_tw, skip_pair, skip_single = self._gua035_solo_wind_pick(
                actionList, threetwo_actionlist, trips_actionlist, pair_actionlist, opponent_rests,
            )
            if idx > 0:
                return idx
            if not skip_single and len(single_actionlist):
                idx = getindex("Single", single_actionlist, actionList)
                if idx > 0:
                    self._dbg(f"GUA-035 solo wind single -> {idx}")
                    return idx

        if not solo_wind and len(single_for_play) and card_val[single_for_play[0][0]] < cur[0]:
            if numofnext == 1:
                pass
            else:
                return getindex("Single", single_for_play, actionList)

        if len(threepair_actionlist) or len(twotrips_actionlist):
            index = rankfour(twotrips_actionlist, threepair_actionlist, actionList, cur[1], cur[2])
            if index is None:
                pass
            else:
                return index

        if len(straight_actionlist) and card_val2[straight_actionlist[0][0]] < cur[4]:
            return getindex("Straight", straight_actionlist, actionList)

        if len(threetwo_actionlist) and not solo_wind:
            index = rankthree(single_actionlist, pair_actionlist, trips_actionlist, threetwo_actionlist, actionList,
                              numofnext, rank, cur[0], cur[3], cur[4], cur[5], cur[-1])
            if index is None:
                pass
            else:
                return index
        if len(trips_actionlist) and not solo_wind:
            return rankone(single_actionlist, trips_actionlist, actionList, numofnext, rank)
        if len(pair_actionlist) and not solo_wind:
            return ranktwo(handcards, single_actionlist, pair_actionlist, trips_actionlist, actionList, numofnext, rank, max_val)
        if len(single_actionlist):
            if numofnext == 1 and len(trips_actionlist) == 0 and len(pair_actionlist) == 0 and rank_card in handcards:
                for i in range(len(actionList)):
                    if actionList[i][0] == 'Pair' and (actionList[i][-1][0] in sorted_cards['Single'] or actionList[i][-1][-1] in sorted_cards['Single']):
                        return i

            if numofnext == 1:
                if len(trips_actionlist) == 0 and len(pair_actionlist) == 0 and rank_card not in handcards:
                    for acti in range(len(actionList)):
                        if len(actionList[acti][-1]) > 1 and actionList[acti][0] != 'Bomb':
                            return acti
                now_max_act_value = 0
                now_max_act_key = 0
                for acti in range(len(actionList)):
                    if actionList[acti][0] == 'Single' and actionList[acti][-1][0] in sorted_cards['Single']:
                        if card_val[actionList[acti][1]] > now_max_act_value:
                            now_max_act_value = card_val[actionList[acti][1]]
                            now_max_act_key = acti

                return now_max_act_key

            if single_for_play:
                return getindex("Single", single_for_play, actionList)
            return 0
        else:
            self._dbg("_active else branch -> 0")
            return 0

    def _get_list(self, handcards, rank):
        single_actionlist = []
        pair_actionlist = []
        trips_actionlist = []
        threepair_actionlist = []
        threetwo_actionlist = []
        twotrips_actionlist = []
        straight_actionlist = []

        action2 = "None"
        action3 = "None"

        rank_card = 'H' + str(rank)

        card_val = CARD_VALUE_S2V.copy()
        card_val2 = CARD_VALUE_S2V2.copy()
        card_val[rank_card[-1]] = 15
        sorted_cards, bomb_info = combine_handcards(handcards, rank, card_val)

        def mysort(elem):
            return card_val[elem[0]]

        def mysort1(elem):
            return card_val2[elem[0]]

        if sorted_cards["Single"]:
            for singlecard in sorted_cards['Single']:
                single_actionlist.append([singlecard[-1], singlecard])
            single_actionlist.sort(key=mysort)

        if sorted_cards["Pair"]:
            for paircard in sorted_cards['Pair']:
                pair_actionlist.append([paircard[0][-1], paircard])
            pair_actionlist.sort(key=mysort)

        if sorted_cards['Trips']:
            for tripcard in sorted_cards['Trips']:
                trips_actionlist.append([tripcard[0][-1], tripcard])
            trips_actionlist.sort(key=mysort)

        if sorted_cards['Pair'] and sorted_cards['Trips']:
            for tripcard in sorted_cards['Trips']:
                for paircard in sorted_cards['Pair']:
                    threetwo_actionlist.append([tripcard[0][-1], tripcard + paircard])
            threetwo_actionlist.sort(key=mysort)

        if len(sorted_cards['Pair']) >= 3:
            for i in range(len(pair_actionlist) - 2):
                if card_val[pair_actionlist[i][0]] == card_val[pair_actionlist[i + 1][0]] - 1 and \
                        card_val[pair_actionlist[i + 1][0]] == card_val[pair_actionlist[i + 2][0]] - 1:
                    action2 = pair_actionlist[i][-1] + pair_actionlist[i + 1][-1] + pair_actionlist[i + 2][-1]
                    threepair_actionlist.append([action2[0][-1], action2])
            threepair_actionlist.sort(key=mysort1)

        if len(sorted_cards['Trips']) >= 2:
            for i in range(len(trips_actionlist) - 1):
                if card_val[trips_actionlist[i][0]] == card_val[trips_actionlist[i + 1][0]] - 1:
                    action3 = trips_actionlist[i][-1] + trips_actionlist[i + 1][-1]
                    twotrips_actionlist.append([action3[0][-1], action3])
            twotrips_actionlist.sort(key=mysort1)

        if 'Straight' in sorted_cards.keys() and sorted_cards['Straight']:
            for straightcard in sorted_cards['Straight']:
                straight_actionlist.append([straightcard[0][-1], straightcard])
            straight_actionlist.sort(key=mysort1)

        return sorted_cards, single_actionlist, pair_actionlist, trips_actionlist, threepair_actionlist, threetwo_actionlist, twotrips_actionlist, straight_actionlist

    def _back_action(self, data):
        rank = data.get("curRank", "2")
        action_list = data.get("actionList", [])
        handCards = data.get("handCards", [])
        card_val = CARD_VALUE_S2V.copy()
        card_val[rank] = 15

        def flag_TJQ(handCards_X):
            flag_T = False
            flag_J = False
            flag_Q = False
            for i in range(len(handCards_X)):
                if handCards_X[i][0][-1] == "T":
                    flag_T = True
                if handCards_X[i][0][-1] == "J":
                    flag_J = True
                if handCards_X[i][0][-1] == "Q":
                    flag_Q = True
            return flag_T, flag_J, flag_Q

        def get_card_index(target):
            for i in range(len(action_list)):
                if action_list[i][2][0] == target:
                    return i

        def choose_in_single(single_list):
            for my_pos in (self.tribute_result or []):
                if my_pos[1] == self.player_id:
                    tribute_pos = my_pos[0]

            n = len(single_list)
            if (int(tribute_pos) + self.player_id) % 2 != 0:
                for card in single_list:
                    if card in ['H5', 'HT']:
                        return card
                    elif card in ['S5', 'C5', 'D5', 'ST', 'CT', 'DT']:
                        return card
                return single_list[randint(0, n - 1)]
            else:
                back_list = []
                for card in single_list:
                    if card[-1] != 'T':
                        if int(card[-1]) < 5:
                            back_list.append(card)
                if back_list:
                    return back_list[randint(0, len(back_list) - 1)]
                return single_list[randint(0, n - 1)]

        def choose_in_pair(pair_list, pair_list_from_handcards):
            val_dict = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "T": 10}
            if len(pair_list) < 3:
                return pair_list[0][0]
            for i in range(len(pair_list)):
                flag = False
                if i >= 2:
                    pair_first_val, pair_second_val, pair_third_val = pair_list[i - 2][0][-1], pair_list[i - 1][0][-1], \
                    pair_list[i][0][-1]
                    if val_dict[pair_first_val] == val_dict[pair_second_val] - 1 and val_dict[pair_second_val] == \
                            val_dict[pair_third_val] - 1:
                        flag = True
                if 1 <= i <= len(pair_list) - 2:
                    pair_first_val, pair_second_val, pair_third_val = pair_list[i - 1][0][-1], pair_list[i][0][-1], \
                    pair_list[i + 1][0][-1]
                    if val_dict[pair_first_val] == val_dict[pair_second_val] - 1 and val_dict[pair_second_val] == \
                            val_dict[pair_third_val] - 1:
                        flag = True
                if i <= len(pair_list) - 3:
                    pair_first_val, pair_second_val, pair_third_val = pair_list[i][0][-1], pair_list[i + 1][0][-1], \
                    pair_list[i + 2][0][-1]
                    if val_dict[pair_first_val] == val_dict[pair_second_val] - 1 and val_dict[pair_second_val] == \
                            val_dict[pair_third_val] - 1:
                        flag = True
                if pair_list[i][0][-1] == '9':
                    flag_T, flag_J, flag_Q = flag_TJQ(pair_list_from_handcards)
                    if flag_T and flag_J:
                        flag = True
                if pair_list[i][0][-1] == 'T':
                    flag_T, flag_J, flag_Q = flag_TJQ(pair_list_from_handcards)
                    if flag_J and flag_Q:
                        flag = True
                if flag:
                    continue
                else:
                    return pair_list[i][0]
            return pair_list[0][0]

        def choose_in_trips(trips_list, trips_list_from_handcards):
            val_dict = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "T": 10}
            if len(trips_list) < 2:
                return trips_list[0][0]
            for i in range(len(trips_list)):
                flag = False
                if i >= 1:
                    pair_first_val, pair_second_val = trips_list[i - 1][0][-1], trips_list[i][0][-1]
                    if val_dict[pair_first_val] == val_dict[pair_second_val] - 1:
                        flag = True
                if i <= len(trips_list) - 2:
                    pair_first_val, pair_second_val = trips_list[i][0][-1], trips_list[i + 1][0][-1]
                    if val_dict[pair_first_val] == val_dict[pair_second_val] - 1:
                        flag = True
                if trips_list[i][0][-1] == 'T':
                    flag_T, flag_J, flag_Q = flag_TJQ(trips_list_from_handcards)
                    if flag_J:
                        flag = True
                if flag:
                    continue
                else:
                    return trips_list[i][0]
            return trips_list[0][0]

        def choose_in_bomb(bomb_list, bomb_info):
            def get_card_from_bomb(bomb_list, key):
                for bomb in bomb_list:
                    for card in bomb:
                        if card[-1] == key:
                            return card

            for key, value in bomb_info:
                if value > 4:
                    return get_card_from_bomb(bomb_list, key)
            return bomb_list[0][0]

        combined_handcards, handCards_bomb_info = combine_handcards(handCards, rank, card_val)

        combined_temp = {"Single": [], "Trips": [], "Pair": [], "Bomb": []}
        temp_bomb_info = {}
        for card in combined_handcards["Single"]:
            if card_val[card[-1]] <= 10:
                combined_temp["Single"].append(card)
        for trips_card in combined_handcards["Trips"]:
            if card_val[trips_card[0][-1]] <= 10:
                combined_temp["Trips"].append(trips_card)
        for pair_card in combined_handcards["Pair"]:
            if card_val[pair_card[0][-1]] <= 10:
                combined_temp["Pair"].append(pair_card)
        for bomb_card in combined_handcards["Bomb"]:
            if card_val[bomb_card[0][-1]] <= 10:
                combined_temp["Bomb"].append(bomb_card)
        for key, values in handCards_bomb_info.items():
            if card_val[key] <= 10:
                temp_bomb_info[key] = values

        card = None
        if combined_temp["Single"]:
            card = choose_in_single(combined_temp["Single"])
        elif combined_temp["Trips"]:
            card = choose_in_trips(combined_temp["Trips"], combined_handcards["Trips"])
        elif combined_temp["Pair"]:
            card = choose_in_pair(combined_temp["Pair"], combined_handcards["Pair"])
        elif combined_temp["Bomb"]:
            card = choose_in_bomb(combined_temp["Bomb"], temp_bomb_info)
        else:
            temp = []
            for handCard in handCards:
                if card_val[handCard[-1]] <= 10:
                    temp.append(handCard)
            card = temp[randint(0, len(temp) - 1)]
        return get_card_index(card)

    def _tribute(self, data):
        action_list = data.get("actionList", [])
        rank = data.get("curRank", "2")
        rank_card = 'H' + str(rank)
        first_action = action_list[0]
        if rank_card in first_action[2]:
            return 1
        else:
            return 0
