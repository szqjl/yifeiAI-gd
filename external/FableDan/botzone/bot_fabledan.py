# -*- coding: utf-8 -*-
"""FableDan botzone bot (python3, numpy only).

Protocol: https://wiki.botzone.org.cn/index.php?title=GuanDan
Default: single-turn (traditional) mode -- works regardless of the
允许长时运行 checkbox. Pass --keep-running for long-running local tests.

Weights: looks for 'data/fabledan_weights.npz' (botzone user storage),
then a local file next to this script; falls back to rule-based play.
"""

import json
import os
import sys
import gc

import numpy as np

# When packed for botzone, the fabledan package sits next to __main__.py;
# for local testing it sits in the parent directory.
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)
sys.path.insert(0, os.path.dirname(_here))

from fabledan.cards import level_rank, order_of, rank_of, is_wildcard
from fabledan.combos import PASS, PASS_MOVE, classify_claim, claim_ids, gen_moves
from fabledan.engine import default_return_card, forced_tribute_card
from fabledan.encode import encode_decision, encode_flat

# botzone's sandbox may close stderr; ANY direct write would then raise and
# kill the bot. All diagnostics must go through _log (safe, never raises)
# and DIAG (surfaced via the JSON debug field, which IS reliable).
DIAG = []


_VERBOSE = ("--verbose" in sys.argv) or ("--keep-running" in sys.argv)


def _log(msg):
    DIAG.append(str(msg)[:300])
    del DIAG[:-6]
    # NEVER touch stderr on botzone: a failed write poisons the stream and
    # the interpreter's exit-time flush then fails -> exit code 120 -> RE.
    if _VERBOSE:
        try:
            sys.stderr.write(str(msg) + "\n")
            sys.stderr.flush()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# model loading
# ---------------------------------------------------------------------------

def _classify_weights(z):
    keys = set(z.files)
    if "token_emb.weight" in keys:
        from fabledan.model_np import NumpyModel
        return ("transformer", NumpyModel({k: z[k] for k in z.files}))
    if "W0" in keys:
        from fabledan.train_demo import NumpyMLP
        m = NumpyMLP()
        m.W = [z["W0"], z["W1"], z["W2"]]
        m.b = [z["b0"], z["b1"], z["b2"]]
        return ("mlp", m)
    return ("rule", None)


def _load_model():
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join("data", "fabledan_weights.npz"),
        os.path.join(here, "fabledan_weights.npz"),
        os.path.join(here, "data", "fabledan_weights.npz"),
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return _classify_weights(np.load(path, allow_pickle=False))
            except Exception:
                pass
    # running from inside a zip (botzone zip upload with embedded weights)
    try:
        import io
        import zipfile
        zpath = here
        while zpath and not os.path.isfile(zpath):
            nxt = os.path.dirname(zpath)
            if nxt == zpath:
                zpath = ""
                break
            zpath = nxt
        if zpath and zipfile.is_zipfile(zpath):
            with zipfile.ZipFile(zpath) as zf:
                if "fabledan_weights.npz" in zf.namelist():
                    buf = io.BytesIO(zf.read("fabledan_weights.npz"))
                    return _classify_weights(np.load(buf, allow_pickle=False))
    except Exception:
        pass
    return ("rule", None)


# ---------------------------------------------------------------------------
# game state mirror
# ---------------------------------------------------------------------------

class Mirror:
    def __init__(self):
        self.my_id = None
        self.lv = 0
        self.hand = []
        self.events = []
        self.left = [27, 27, 27, 27]
        self.done = []
        self.applied_tributes = set()
        self.cur_lead = None     # Move to beat (None = lead freely)

    # -- helpers --
    def _apply_global(self, g):
        for key, ev_name in (("tribute_cards", "tribute"),
                             ("return_cards", "return")):
            d = g.get(key) or {}
            for pid_s, cards in sorted(d.items()):
                pid = int(pid_s)
                if cards is None:
                    continue
                # Botzone protocol: tribute/return values are lists of cards
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
                    else:  # return
                        if pid == self.my_id:
                            if card in self.hand:
                                self.hand.remove(card)
                        elif self._return_receiver(g, pid) == self.my_id:
                            if card not in self.hand:
                                self.hand.append(card)

    @staticmethod
    def _first_card(v):
        """Extract the first (and only) card from a tribute/return value."""
        if isinstance(v, list) and v:
            return v[0]
        if isinstance(v, int) and v >= 0:
            return v
        return -1

    def _tribute_receiver(self, g, payer):
        first = int(g.get("first", -1) if g.get("first") is not None else -1)
        tc = g.get("tribute_cards") or {}
        items = [(int(k), self._first_card(v)) for k, v in tc.items()]
        items = [(k, v) for k, v in items if v >= 0]
        if len(items) <= 1:
            return first
        # double tribute: bigger card -> first, tie -> last's card to first
        last = int(g.get("last", -1) if g.get("last") is not None else -1)
        items.sort(key=lambda kv: (order_of(rank_of(kv[1]), self.lv),
                                   1 if kv[0] == last else 0), reverse=True)
        if items[0][0] == payer:
            return first
        return (first + 2) % 4

    def _return_receiver(self, g, returner):
        # returner gives back to the payer matched with them
        first = int(g.get("first", -1) if g.get("first") is not None else -1)
        tc = g.get("tribute_cards") or {}
        items = [(int(k), self._first_card(v)) for k, v in tc.items()]
        items = [(k, v) for k, v in items if v >= 0]
        if len(items) == 1:
            return items[0][0]
        if len(items) == 2:
            last = int(g.get("last", -1) if g.get("last") is not None else -1)
            items.sort(key=lambda kv: (order_of(rank_of(kv[1]), self.lv),
                                       1 if kv[0] == last else 0), reverse=True)
            big_payer, small_payer = items[0][0], items[1][0]
            if returner == first:
                return big_payer
            return small_payer
        return -1

    def _apply_history(self, hist):
        """Apply new moves from a play request's history.

        Two formats exist in the wild:
        - wiki format: [{"player": p, "response": [action, claim]}, ...]
        - REAL botzone judge format (observed in match logs): a positional
          list of 4 response arrays; slot i belongs to player
          (my_id + i) % 4 (slot 0 = self, 1 = next, 2 = partner, 3 = prev);
          [] means that seat made no move in this window.
        """
        if not hist:
            return
        if any(isinstance(h, dict) for h in hist):
            # wiki dict format: apply entries after our own last entry
            start = 0
            for i, h in enumerate(hist):
                if isinstance(h, dict) and \
                        int(h.get("player", -1)) == self.my_id:
                    start = i + 1
            for h in hist[start:]:
                if isinstance(h, dict):
                    self._apply_move(int(h["player"]), h["response"])
            return
        # positional 4-slot format
        n = len(hist) or 4
        for i, entry in enumerate(hist):
            if i == 0:
                continue   # slot 0 = our own previous move, already applied
            if not isinstance(entry, list) or len(entry) != 2:
                continue   # [] -> no move from that seat
            p = (self.my_id + i) % n
            self._apply_move(p, entry)

    def _apply_move(self, pid, resp):
        action, claim = resp[0], resp[1]
        if not claim:
            self.events.append(("pass", pid))
            return
        mv = classify_claim(action, claim, self.lv)
        self.events.append(("play", pid, mv))
        self.left[pid] -= len(action)
        self.cur_lead = mv
        self._lead_pid = pid

    def feed_request(self, req, my_resp=None):
        """Process one request (and the response we gave to it, if replaying)."""
        stage = req.get("stage")
        g = req.get("global") or {}
        if "your_id" in req:
            self.my_id = int(req["your_id"])
        if "level" in g and g["level"] is not None:
            self.lv = level_rank(g["level"])
        if stage == "deal":
            # New game: reset all round-level state.
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
            # Non-play stages (tribute, return): reset round-level flags
            # so stale values from the previous round don't leak.
            self._pass_on = -1
            self.cur_lead = None
            self._lead_pid = -1
        if my_resp is not None:
            self._apply_my_response(stage, my_resp)

    def _apply_my_response(self, stage, resp):
        if stage == "play" and isinstance(resp, list) and len(resp) == 2 \
                and isinstance(resp[0], list):
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
            # already handled via global tribute_cards next turn; remove now
            card = resp[0]
            if card in self.hand:
                self.hand.remove(card)
                self.applied_tributes.add(
                    ("tribute" if stage == "tribute" else "return",
                     self.my_id, card))
                self.events.append((
                    "tribute" if stage == "tribute" else "return",
                    self.my_id, rank_of(card)))

    # -- decision --
    def lead_to_beat(self):
        """Move we must beat, or None if we lead."""
        # cur_lead only contains plays made AFTER our own last move, so:
        #   someone played since our last turn -> beat cur_lead
        #   nobody played since our last turn  -> we lead freely
        # NOTE: do NOT use pass_on here. The platform sets pass_on the
        # moment the finishing player's last card hits the table, while
        # that play must STILL be beaten. The wind (接风) reaches us in a
        # later request whose window has no play after our own move, and
        # cur_lead is naturally None then.
        if self.cur_lead is None:
            return None
        if getattr(self, "_lead_pid", -1) == self.my_id:
            return None
        return self.cur_lead

    def obs(self, legal, lead):
        done_flags = [p in self.done for p in range(4)]
        return {
            "player": self.my_id,
            "level": self.lv,
            "hand": list(self.hand),
            "legal": legal,
            "lead": lead,
            "lead_owner": getattr(self, "_lead_pid", -1),
            "events": self.events,
            "done": done_flags,
            "left": list(self.left),
        }


# ---------------------------------------------------------------------------
# decision logic
# ---------------------------------------------------------------------------

MODEL_KIND, MODEL = _load_model()


MAX_LEGAL = 128   # cap legal moves to bound q_head memory


def choose_play(mirror):
    lead = mirror.lead_to_beat()
    legal = gen_moves(mirror.hand, mirror.lv, lead)

    # --- cap legal moves for memory safety ---
    if len(legal) > MAX_LEGAL and MODEL_KIND == "transformer":
        # Keep PASS + a diverse subset (prefer different types)
        from fabledan.combos import PASS as _PASS_TYPE
        keep = [m for m in legal if m.type == _PASS_TYPE]
        by_type = {}
        for m in legal:
            if m.type != _PASS_TYPE:
                by_type.setdefault(m.type, []).append(m)
        slots = (MAX_LEGAL - len(keep)) // max(len(by_type), 1)
        for moves in by_type.values():
            keep.extend(moves[:max(slots, 1)])
        legal = keep[:MAX_LEGAL]

    # --- debug log (safe; stderr may be unusable on botzone) ---
    lead_info = "none" if lead is None else repr(lead)
    _log("choose_play: hand=%d legal=%d lead=%s pass_on=%d lead_pid=%d done=%s"
         % (len(mirror.hand), len(legal), lead_info,
            getattr(mirror, "_pass_on", -1),
            getattr(mirror, "_lead_pid", -1),
            getattr(mirror, "done", [])))

    if len(legal) == 1:
        mv = legal[0]
    elif MODEL_KIND == "transformer":
        try:
            toks, feats = encode_decision(mirror.obs(legal, lead))
            q = MODEL.q_values(toks, feats)
            mv = legal[int(np.argmax(q))]
        except Exception:
            import traceback
            _log("model inference failed: " + traceback.format_exc())
            from fabledan.agents import RuleAgent
            mv = legal[RuleAgent().act(mirror.obs(legal, lead))]
        finally:
            gc.collect()
    elif MODEL_KIND == "mlp":
        o = mirror.obs(legal, lead)
        X = np.stack([encode_flat(o, m) for m in legal])
        q, _ = MODEL.forward(X)
        mv = legal[int(np.argmax(q))]
    else:
        from fabledan.agents import RuleAgent
        mv = legal[RuleAgent().act(mirror.obs(legal, lead))]
    if mv.type == PASS:
        return [[], []]
    return [list(mv.cards), list(claim_ids(mv))]


def respond(mirror, req):
    stage = req.get("stage")
    if stage == "deal":
        return []
    if stage == "tribute":
        return [forced_tribute_card(mirror.hand, mirror.lv)]
    if stage == "return":
        return [default_return_card(mirror.hand, mirror.lv)]
    if stage == "play":
        return choose_play(mirror)
    return []


# ---------------------------------------------------------------------------
# main loop
# ---------------------------------------------------------------------------

def main():
    mirror = Mirror()
    first_turn = True
    line = sys.stdin.readline()
    data = json.loads(line)
    if isinstance(data, dict) and "requests" in data:
        reqs = data["requests"]
        resps = data.get("responses") or []
        for i in range(len(resps)):
            mirror.feed_request(reqs[i], resps[i])
        cur = reqs[len(resps)]
    else:
        cur = data
    # Default = single-turn (traditional) mode: one JSON line, then exit.
    # This works on botzone REGARDLESS of the 允许长时运行 checkbox (that
    # checkbox silently resets when uploading a new bot version, so we must
    # not depend on it). --keep-running enables long-running for local tests.
    keep_running = "--keep-running" in sys.argv
    while True:
        try:
            mirror.feed_request(cur)
            action = respond(mirror, cur)
            mirror._apply_my_response(cur.get("stage"), action
                                      if cur.get("stage") != "deal" else None)
        except Exception:
            import traceback
            _log("unhandled: " + traceback.format_exc())
            # return a safe fallback
            stage = cur.get("stage") if "cur" in dir() else "play"
            if stage == "play":
                from fabledan.agents import RuleAgent
                lead = mirror.lead_to_beat() if hasattr(mirror, 'lead_to_beat') else None
                legal = gen_moves(mirror.hand, mirror.lv, lead)
                mv = legal[RuleAgent().act(mirror.obs(legal, lead))]
                action = [[], []] if mv.type == 0 else [list(mv.cards), list(claim_ids(mv))]
            elif stage == "deal":
                action = []
            elif stage in ("tribute", "return"):
                action = [mirror.hand[0]] if mirror.hand else []
            else:
                action = []
        out = {"response": action}
        dbg = "FableDan model=%s" % MODEL_KIND
        if DIAG:
            dbg += " | " + " || ".join(DIAG)
        out["debug"] = dbg[:1000]
        first_turn = False
        print(json.dumps(out))
        if not keep_running:
            # hard-exit 0: skip interpreter-shutdown stream flushing, which
            # can fail (exit 120) if the platform closed our pipes already.
            try:
                sys.stdout.flush()
            except Exception:
                pass
            os._exit(0)
        print(">>>BOTZONE_REQUEST_KEEP_RUNNING<<<")
        sys.stdout.flush()
        line = sys.stdin.readline()
        if not line:
            return
        data = json.loads(line)
        if isinstance(data, dict) and "requests" in data:
            reqs = data["requests"]
            cur = reqs[-1]
        else:
            cur = data


if __name__ == "__main__":
    main()
