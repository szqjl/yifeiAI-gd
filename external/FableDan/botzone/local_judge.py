# -*- coding: utf-8 -*-
"""Local Botzone-GuanDan judge simulator.

Runs 4 bot subprocesses with the botzone JSON protocol (long-running mode)
and verifies every response is legal. Usage:

    python botzone/local_judge.py --bot "python3 botzone/bot_fabledan.py" --games 5
"""

import argparse
import json
import random
import subprocess
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from fabledan.cards import RANK_NAMES, level_rank, order_of, rank_of, is_wildcard
from fabledan.combos import PASS, beats, classify_claim, gen_moves
from fabledan.engine import partner, forced_tribute_card
from fabledan.cards import BJ


class BotProc:
    """Long-running-mode bot process (fast local testing)."""

    def __init__(self, cmd):
        self.p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, text=True,
                                  bufsize=1)
        self.started = False

    def turn(self, request):
        if not self.started:
            payload = json.dumps({"requests": [request], "responses": []})
            self.started = True
        else:
            payload = json.dumps(request)
        self.p.stdin.write(payload + "\n")
        self.p.stdin.flush()
        resp_line = self.p.stdout.readline()
        if not resp_line:
            raise RuntimeError("bot died: " + str(self.p.stderr))
        out = json.loads(resp_line)
        marker = self.p.stdout.readline()  # keep-running marker
        if ">>>BOTZONE_REQUEST_KEEP_RUNNING<<<" not in marker:
            raise RuntimeError("missing keep-running marker, got: " + marker)
        return out["response"]

    def close(self):
        try:
            self.p.kill()
        except Exception:
            pass


class TradBotProc:
    """Traditional-mode bot: fresh process each turn, full history replay.
    Exactly mirrors the real botzone GuanDan judge behaviour."""

    def __init__(self, cmd):
        self.cmd = cmd
        self.requests = []
        self.responses = []

    def turn(self, request):
        self.requests.append(request)
        payload = json.dumps({"requests": self.requests,
                              "responses": self.responses})
        p = subprocess.Popen(self.cmd, shell=True, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, text=True)
        out_text, _ = p.communicate(payload + "\n", timeout=60)
        lines = [ln for ln in out_text.splitlines() if ln.strip()]
        if len(lines) != 1:
            raise RuntimeError("traditional mode must print exactly one "
                               "JSON line, got: %r" % out_text)
        resp = json.loads(lines[0])["response"]
        self.responses.append(resp)
        return resp

    def close(self):
        pass


def run_game(bot_cmds, seed, level_str="2", tribute_mode=None, verbose=False,
             traditional=False):
    rng = random.Random(seed)
    lv = level_rank(level_str)
    deck = list(range(108))
    rng.shuffle(deck)
    hands = [sorted(deck[i*27:(i+1)*27]) for i in range(4)]
    if traditional:
        # fresh process per turn + full history replay (= real botzone judge)
        bots = [TradBotProc(c + " --single-turn") for c in bot_cmds]
    else:
        # long-running mode keeps the 4 processes alive (fast local testing)
        bots = [BotProc(c + " --keep-running") for c in bot_cmds]

    n_trib = 0
    first = last = -1
    if tribute_mode:
        kind, last, first = tribute_mode
        n_trib = 1 if kind == 'single' else 2

    g = {"level": level_str, "tribute": n_trib, "first": first, "last": last}
    tribute_cards = {}
    return_cards = {}
    resist = False

    # --- deal ---
    for p in range(4):
        req = {"stage": "deal", "deliver": hands[p], "your_id": p,
               "global": dict(g)}
        r = bots[p].turn(req)
        assert r == [], "deal response must be []"

    lead_player = 0
    # --- tribute phase ---
    if n_trib:
        payers = [last] if n_trib == 1 else [last, partner(last)]
        receivers = [first] if n_trib == 1 else [first, partner(first)]
        n_bj = sum(1 for p in payers for c in hands[p] if rank_of(c) == BJ)
        if n_bj >= 2:
            resist = True
            lead_player = first
            for p in payers:
                tribute_cards[str(p)] = -1
        else:
            got = {}
            for p in payers:
                gg = dict(g); gg["tribute_cards"] = {str(k): v for k, v in tribute_cards.items()}
                gg["return_cards"] = {}; gg["resist"] = False
                r = bots[p].turn({"stage": "tribute", "global": gg})
                card = r[0]
                exp = forced_tribute_card(hands[p], lv)
                assert order_of(rank_of(card), lv) == order_of(rank_of(exp), lv), \
                    "tribute card not max: %s vs %s" % (card, exp)
                assert card in hands[p] and not is_wildcard(card, lv)
                hands[p].remove(card)
                tribute_cards[str(p)] = card
                got[p] = card
            # pair payers to receivers
            if n_trib == 1:
                pairs = [(payers[0], first)]
                lead_player = payers[0]
            else:
                o0 = order_of(rank_of(got[payers[0]]), lv)
                o1 = order_of(rank_of(got[payers[1]]), lv)
                if o1 > o0:
                    pairs = [(payers[1], first), (payers[0], partner(first))]
                    lead_player = payers[1]
                else:
                    pairs = [(payers[0], first), (payers[1], partner(first))]
                    lead_player = payers[0]
            for payer, recv in pairs:
                hands[recv].append(got[payer])
                gg = dict(g)
                gg["tribute_cards"] = {str(k): v for k, v in tribute_cards.items()}
                gg["return_cards"] = {str(k): v for k, v in return_cards.items()}
                gg["resist"] = False
                r = bots[recv].turn({"stage": "return", "global": gg})
                card = r[0]
                assert card in hands[recv], "return card not in hand"
                assert rank_of(card) <= 9, "return must be face <= 10"
                hands[recv].remove(card)
                hands[payer].append(card)
                return_cards[str(recv)] = card

    # --- play phase ---
    full_g = dict(g)
    full_g["tribute_cards"] = {str(k): v for k, v in tribute_cards.items()}
    full_g["return_cards"] = {str(k): v for k, v in return_cards.items()}
    full_g["resist"] = resist

    history = []          # list of {"player": p, "response": [a, c]}
    done_order = []
    done = [False] * 4
    cur = lead_player
    lead_move = None
    lead_owner = None
    pass_on = -1
    moves = 0
    while len(done_order) < 3 and moves < 600:
        moves += 1
        if lead_move is not None and cur == lead_owner:
            if done[cur]:
                nxt = partner(cur)
                if done[nxt]:
                    nxt = (cur + 1) % 4
                    while done[nxt]:
                        nxt = (nxt + 1) % 4
                pass_on = cur
                cur = nxt
            lead_move = None
            lead_owner = None
            continue
        # real botzone judge format: positional 4-slot history,
        # slot i = latest move of player (cur+i)%4 in the current window
        slots = [[], [], [], []]
        last_self = -1
        for idx in range(len(history) - 1, -1, -1):
            if history[idx]["player"] == cur:
                last_self = idx
                break
        if last_self >= 0:
            slots[0] = history[last_self]["response"]
        for h in history[last_self + 1:] if last_self >= 0 else history:
            slots[(h["player"] - cur) % 4] = h["response"]
        req = {"stage": "play", "history": slots,
               "done": list(done_order), "pass_on": pass_on,
               "global": full_g}
        r = bots[cur].turn(req)
        action, claim = r
        if claim:
            mv = classify_claim(action, claim, lv)
            # verify all cards in hand & legal beat
            for c in action:
                assert c in hands[cur], "card %d not in hand of %d" % (c, cur)
            legal_check = beats(mv, lead_move, lv) if lead_move is not None \
                else mv.type != PASS
            assert legal_check, "illegal move by %d: %s over %s" % (cur, mv, lead_move)
            for c in action:
                hands[cur].remove(c)
            lead_move = mv
            lead_owner = cur
            pass_on = -1
            if not hands[cur]:
                done[cur] = True
                done_order.append(cur)
                # real platform sets pass_on the moment the finishing
                # player's last card hits the table (their play must
                # still be beaten by the others)
                pass_on = cur
                if len(done_order) == 2 and done_order[1] == partner(done_order[0]):
                    history.append({"player": cur, "response": r})
                    break
        else:
            assert lead_move is not None, "cannot pass when leading"
        history.append({"player": cur, "response": r})
        cur = (cur + 1) % 4
        while done[cur] and cur != lead_owner:
            cur = (cur + 1) % 4

    for b in bots:
        b.close()
    rest = [p for p in range(4) if p not in done_order]
    ranking = done_order + rest
    first_team = ranking[0] % 2
    pos_partner = ranking.index(partner(ranking[0]))
    score = {1: 3, 2: 2, 3: 1}[pos_partner]
    if verbose:
        print("ranking:", ranking, "team", first_team, "+%d" % score)
    return ranking, first_team, score


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bot", required=True, help="command for all 4 seats")
    ap.add_argument("--bot-b", default="", help="command for seats 1,3")
    ap.add_argument("--games", type=int, default=5)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--traditional", action="store_true",
                    help="fresh process per turn (= real botzone judge)")
    args = ap.parse_args()
    teamA_wins = 0
    for gi in range(args.games):
        rng = random.Random(args.seed + gi)
        level = RANK_NAMES[rng.randrange(13)]
        tm = None
        x = rng.random()
        if x > 1/3:
            first = rng.randrange(4)
            last = rng.choice([p for p in range(4) if (p - first) % 2 == 1])
            tm = ('single' if x < 2/3 else 'double', last, first)
        cmds = [args.bot if p % 2 == 0 or not args.bot_b else args.bot_b
                for p in range(4)]
        ranking, team, score = run_game(cmds, seed=1000 + gi,
                                        level_str=level, tribute_mode=tm,
                                        verbose=True,
                                        traditional=args.traditional)
        if team == 0:
            teamA_wins += 1
    print("team A (seats 0,2) wins: %d/%d" % (teamA_wins, args.games))


if __name__ == "__main__":
    main()
