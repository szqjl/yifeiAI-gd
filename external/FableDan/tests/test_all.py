# -*- coding: utf-8 -*-
"""Smoke tests: python tests/test_all.py  (or pytest)."""
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from fabledan.combos import gen_moves, classify_claim, claim_ids, TYPE_NAMES
from fabledan.encode import encode_decision, VOCAB
from fabledan.engine import play_round
from fabledan.agents import RandomAgent, RuleAgent


def test_claim_roundtrip():
    rng = random.Random(7)
    deck = list(range(108))
    for _ in range(300):
        rng.shuffle(deck)
        hand, lv = deck[:27], rng.randrange(13)
        for m in gen_moves(hand, lv, None):
            ci = claim_ids(m)
            m2 = classify_claim(m.cards, ci, lv)
            assert m2.type == m.type and m2.key == m.key, \
                (TYPE_NAMES[m.type], TYPE_NAMES[m2.type])


def test_engine_invariants():
    for g in range(100):
        agents = [RandomAgent(g * 4 + i) for i in range(4)]
        rewards, ranking, rnd = play_round(agents, rng=random.Random(g))
        assert sorted(rewards) in ([-3, -3, 3, 3], [-2, -2, 2, 2], [-1, -1, 1, 1])
        played = sum(len(e[2].cards) for e in rnd.events if e[0] == 'play')
        assert played + sum(len(h) for h in rnd.hands) == 108


def test_encode():
    def cb(p, obs, legal, idx):
        toks, feats = encode_decision(obs)
        assert all(0 <= t < VOCAB for t in toks)
        assert feats.shape[0] == len(legal)
    for g in range(10):
        play_round([RandomAgent(i) for i in range(4)],
                   rng=random.Random(g), sample_cb=cb)


def test_rule_beats_random():
    from fabledan.evaluate import evaluate
    wr, _ = evaluate(lambda: RuleAgent(), lambda: RandomAgent(0),
                     games=100, seed=1)
    assert wr > 0.7, wr


def test_ring_runner_with_belief():
    import numpy as np
    from fabledan.ring import RingRunner
    rng = np.random.default_rng(0)
    r = RingRunner(ring=4, seed=1, eps=0.05, top_k=5)
    total = 0
    for _ in range(150):
        reqs = r.collect_requests()
        r.step({s: rng.standard_normal(f.shape[0]).astype(np.float32)
                for s, t, f in reqs})
        for toks, feat, z, belief in r.pop_episodes():
            total += 1
            assert belief.shape == (45,) and -1 <= z <= 1
            # normalized counts: per-rank 0..8 cards -> /4 gives 0..2
            assert 0 <= belief.min() and belief.max() <= 2.0
            # three hidden hands hold <= 81 cards in total -> /4
            assert belief.sum() <= 81 / 4 + 1e-5
    assert r.episodes_done > 0 and total > 0


if __name__ == "__main__":
    test_claim_roundtrip(); print("claim roundtrip OK")
    test_engine_invariants(); print("engine invariants OK")
    test_encode(); print("encode OK")
    test_rule_beats_random(); print("rule>random OK")
    test_ring_runner_with_belief(); print("ring+belief OK")
    print("ALL TESTS PASSED")
