# -*- coding: utf-8 -*-
"""V9 Botzone 状态镜像（自 FableDan bot_fabledan.Mirror 适配）。"""

from __future__ import annotations

from typing import List, Optional

from src.v.nn.training.fd_env import ensure_fabledan_importable

ensure_fabledan_importable()
from fabledan.cards import level_rank, order_of, rank_of  # noqa: E402
from fabledan.combos import PASS, classify_claim  # noqa: E402


class BotzoneMirror:
    """从 Botzone requests/responses 重放维护 FableDan 整副状态。"""

    def __init__(self) -> None:
        self.my_id = 0
        self.lv = 0
        self.hand: list[int] = []
        self.left = [27, 27, 27, 27]
        self.events: list = []
        self.done: list[int] = []
        self.applied_tributes: set = set()
        self.cur_lead = None
        self._lead_pid = -1
        self._pass_on = -1

    def _apply_global(self, g: dict) -> None:
        for key, ev_name in (("tribute_cards", "tribute"), ("return_cards", "return")):
            d = g.get(key) or {}
            for pid_s, cards in sorted(d.items()):
                pid = int(pid_s)
                if cards is None:
                    continue
                if not isinstance(cards, list):
                    cards = [cards]
                for card in cards:
                    if card is None or (isinstance(card, int) and card < 0):
                        continue
                    sig = (ev_name, pid, card)
                    if sig in self.applied_tributes:
                        continue
                    self.applied_tributes.add(sig)
                    self.events.append((ev_name, pid, rank_of(card)))
                    if ev_name == "tribute":
                        if pid == self.my_id:
                            if card in self.hand:
                                self.hand.remove(card)
                        elif self._tribute_receiver(g, pid) == self.my_id:
                            if card not in self.hand:
                                self.hand.append(card)
                    else:
                        if pid == self.my_id:
                            if card in self.hand:
                                self.hand.remove(card)
                        elif self._return_receiver(g, pid) == self.my_id:
                            if card not in self.hand:
                                self.hand.append(card)

    @staticmethod
    def _first_card(v) -> int:
        if isinstance(v, list) and v:
            return v[0]
        if isinstance(v, int) and v >= 0:
            return v
        return -1

    def _tribute_receiver(self, g: dict, payer: int) -> int:
        first = int(g.get("first", -1) if g.get("first") is not None else -1)
        tc = g.get("tribute_cards") or {}
        items = [(int(k), self._first_card(v)) for k, v in tc.items()]
        items = [(k, v) for k, v in items if v >= 0]
        if len(items) <= 1:
            return first
        last = int(g.get("last", -1) if g.get("last") is not None else -1)
        items.sort(
            key=lambda kv: (order_of(rank_of(kv[1]), self.lv), 1 if kv[0] == last else 0),
            reverse=True,
        )
        if items[0][0] == payer:
            return first
        return (first + 2) % 4

    def _return_receiver(self, g: dict, returner: int) -> int:
        first = int(g.get("first", -1) if g.get("first") is not None else -1)
        tc = g.get("tribute_cards") or {}
        items = [(int(k), self._first_card(v)) for k, v in tc.items()]
        items = [(k, v) for k, v in items if v >= 0]
        if len(items) == 1:
            return items[0][0]
        if len(items) == 2:
            last = int(g.get("last", -1) if g.get("last") is not None else -1)
            items.sort(
                key=lambda kv: (order_of(rank_of(kv[1]), self.lv), 1 if kv[0] == last else 0),
                reverse=True,
            )
            big_payer, small_payer = items[0][0], items[1][0]
            if returner == first:
                return big_payer
            return small_payer
        return -1

    def _apply_history(self, hist: list) -> None:
        if not hist:
            return
        if any(isinstance(h, dict) for h in hist):
            start = 0
            for i, h in enumerate(hist):
                if isinstance(h, dict) and int(h.get("player", -1)) == self.my_id:
                    start = i + 1
            for h in hist[start:]:
                if isinstance(h, dict):
                    self._apply_move(int(h["player"]), h["response"])
            return
        n = len(hist) or 4
        for i, entry in enumerate(hist):
            if i == 0:
                continue
            if not isinstance(entry, list) or len(entry) != 2:
                continue
            p = (self.my_id + i) % n
            self._apply_move(p, entry)

    def _apply_move(self, pid: int, resp: list) -> None:
        action, claim = resp[0], resp[1]
        if not claim:
            self.events.append(("pass", pid))
            return
        mv = classify_claim(action, claim, self.lv)
        self.events.append(("play", pid, mv))
        self.left[pid] -= len(action)
        self.cur_lead = mv
        self._lead_pid = pid

    def feed_request(self, req: dict, my_resp: Optional[list] = None) -> None:
        stage = req.get("stage")
        g = req.get("global") or {}
        if "your_id" in req:
            self.my_id = int(req["your_id"])
        if "level" in g and g["level"] is not None:
            self.lv = level_rank(g["level"])
        if stage == "deal":
            self.hand = list(req.get("deliver") or [])
            self.done = []
            self.events = []
            self.left = [27, 27, 27, 27]
            self.applied_tributes = set()
            self.cur_lead = None
            self._lead_pid = -1
            self._pass_on = -1
        self._apply_global(g)
        if stage == "play":
            self.done = [int(x) for x in (req.get("done") or [])]
            self.cur_lead = None
            self._lead_pid = -1
            self._apply_history(req.get("history") or [])
            po = req.get("pass_on", -1)
            self._pass_on = int(po) if po is not None else -1
        else:
            self._pass_on = -1
            self.cur_lead = None
            self._lead_pid = -1
        if my_resp is not None:
            self.apply_my_response(stage, my_resp)

    def apply_my_response(self, stage: str, resp: list) -> None:
        if stage == "play" and isinstance(resp, list) and len(resp) == 2 and isinstance(resp[0], list):
            action, claim = resp
            if claim:
                mv = classify_claim(action, claim, self.lv)
                self.events.append(("play", self.my_id, mv))
                for c in action:
                    if c in self.hand:
                        self.hand.remove(c)
                self.left[self.my_id] -= len(action)
            else:
                self.events.append(("pass", self.my_id))
        elif stage in ("tribute", "return") and isinstance(resp, list) and resp:
            card = resp[0]
            if card in self.hand:
                self.hand.remove(card)
                self.applied_tributes.add(
                    ("tribute" if stage == "tribute" else "return", self.my_id, card)
                )
                self.events.append(
                    ("tribute" if stage == "tribute" else "return", self.my_id, rank_of(card))
                )

    def lead_to_beat(self):
        if self.cur_lead is None:
            return None
        if self._lead_pid == self.my_id:
            return None
        return self.cur_lead

    def obs(self, legal: list, lead) -> dict:
        done_flags = [p in self.done for p in range(4)]
        return {
            "player": self.my_id,
            "level": self.lv,
            "hand": list(self.hand),
            "legal": legal,
            "lead": lead,
            "lead_owner": self._lead_pid,
            "events": self.events,
            "done": done_flags,
            "left": list(self.left),
        }
