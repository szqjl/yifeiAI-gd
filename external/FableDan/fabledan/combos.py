# -*- coding: utf-8 -*-
"""Move (一手牌) representation, enumeration with wildcards (配子), comparison.

Move types and fixed sizes:
  PASS      -
  SINGLE    1
  PAIR      2
  TRIPLE    3
  FULL      5   (三带二)
  STRAIGHT  5   (顺子, A=1 or 14)
  PLATE     6   (三连对/木板)
  TUBE      6   (钢板, two consecutive triples)
  BOMB      4..10
  SFLUSH    5   (同花顺)
  ROCKET    4   (4 jokers)
"""

from .cards import (BJ, SJ, NUM_RANKS, SEQV_TO_RANK, is_wildcard, order_of,
                    rank_of, seq_values, suit_of)

PASS, SINGLE, PAIR, TRIPLE, FULL, STRAIGHT, PLATE, TUBE, BOMB, SFLUSH, ROCKET = range(11)
TYPE_NAMES = ["PASS", "SINGLE", "PAIR", "TRIPLE", "FULL", "STRAIGHT",
              "PLATE", "TUBE", "BOMB", "SFLUSH", "ROCKET"]

# bomb tiers: 4bomb < 5bomb < SF < 6bomb < 7 < 8 < 9 < 10 < rocket
_BOMB_TIER = {4: 0, 5: 1, 6: 3, 7: 4, 8: 5, 9: 6, 10: 7}
_SF_TIER = 2
_ROCKET_TIER = 99


class Move:
    __slots__ = ("type", "key", "cards", "claim_ranks", "size")

    def __init__(self, mtype, key, cards, claim_ranks):
        self.type = mtype
        self.key = key                  # comparison key within same type/size
        self.cards = cards              # actual card ids played
        self.claim_ranks = claim_ranks  # claimed rank indices (len == len(cards))
        self.size = len(cards)

    def is_bombish(self):
        return self.type in (BOMB, SFLUSH, ROCKET)

    def bomb_tier(self):
        if self.type == ROCKET:
            return _ROCKET_TIER
        if self.type == SFLUSH:
            return _SF_TIER
        return _BOMB_TIER[self.size]

    def __repr__(self):
        from .cards import RANK_NAMES
        return "%s[%s]" % (TYPE_NAMES[self.type],
                           ",".join(RANK_NAMES[r] for r in self.claim_ranks))


PASS_MOVE = Move(PASS, 0, [], [])


def beats(move, lead, lv):
    """Does `move` beat `lead`?  lead=None means leading (any non-pass ok)."""
    if move.type == PASS:
        return False
    if lead is None or lead.type == PASS:
        return True
    if move.is_bombish():
        if not lead.is_bombish():
            return True
        if move.bomb_tier() != lead.bomb_tier():
            return move.bomb_tier() > lead.bomb_tier()
        return move.key > lead.key
    if lead.is_bombish():
        return False
    if move.type != lead.type or move.size != lead.size:
        return False
    return move.key > lead.key


# ---------------------------------------------------------------------------
# enumeration
# ---------------------------------------------------------------------------

class HandIndex:
    """Pre-indexed hand for fast enumeration."""

    def __init__(self, cards, lv):
        self.lv = lv
        self.wilds = [c for c in cards if is_wildcard(c, lv)]
        self.naturals = [c for c in cards if not is_wildcard(c, lv)]
        self.cnt = [0] * NUM_RANKS
        self.by_rank = [[] for _ in range(NUM_RANKS)]
        self.by_suit_rank = {}
        for c in self.naturals:
            r = rank_of(c)
            self.cnt[r] += 1
            self.by_rank[r].append(c)
            s = suit_of(c)
            if s >= 0:
                self.by_suit_rank.setdefault((s, r), []).append(c)
        self.w = len(self.wilds)

    def pick(self, r, k, wild_used):
        """Pick k cards of rank r, using wildcards for the shortfall."""
        have = self.by_rank[r]
        n_nat = min(len(have), k)
        need = k - n_nat
        if wild_used + need > self.w:
            return None
        cards = have[:n_nat] + self.wilds[wild_used:wild_used + need]
        return cards, [r] * k, wild_used + need


def _claim_card_for_rank(r, used_ids, force_suit=None, avoid_suit=None):
    """A representative card id for a claimed rank (for botzone claim arrays)."""
    for base in (0, 54):
        if r == SJ:
            cid = 52 + base
        elif r == BJ:
            cid = 53 + base
        else:
            cid = None
        if cid is not None:
            if cid not in used_ids:
                used_ids.add(cid)
                return cid
            continue
        if force_suit is not None:
            suits = [force_suit]
        elif avoid_suit is not None:
            suits = [x for x in range(4) if x != avoid_suit]
        else:
            suits = range(4)
        for s in suits:
            cid2 = r * 4 + s + base
            if cid2 not in used_ids:
                used_ids.add(cid2)
                return cid2
    return r * 4 + (force_suit or 0)  # give up on uniqueness


def claim_ids(move):
    """Build the botzone `claim` array (card ids) for a move."""
    used = set()
    out = []
    force_suit = None
    if move.type == SFLUSH:
        for c, r in zip(move.cards, move.claim_ranks):
            if rank_of(c) == r:
                force_suit = suit_of(c)
                break
        if force_suit is None:
            force_suit = 0
    for c, r in zip(move.cards, move.claim_ranks):
        if rank_of(c) == r and (force_suit is None or suit_of(c) == force_suit):
            out.append(c)
            used.add(c)
        else:
            out.append(None)  # wildcard placeholder
    avoid_suit = None
    if move.type == STRAIGHT:
        nat_suits = set(suit_of(c) for c in out if c is not None)
        if len(nat_suits) == 1:
            avoid_suit = nat_suits.pop()
    for i, (c, r) in enumerate(zip(move.cards, move.claim_ranks)):
        if out[i] is None:
            out[i] = _claim_card_for_rank(r, used, force_suit, avoid_suit)
    return out


def gen_moves(cards, lv, lead=None):
    """All legal moves for `cards` under level `lv` against `lead`.

    lead=None -> leading: all combos (no PASS).
    else      -> PASS + all moves beating lead.
    """
    h = HandIndex(cards, lv)
    out = []

    def add(mtype, key, picked, claim):
        out.append(Move(mtype, key, picked, claim))

    # --- singles ---
    for r in range(NUM_RANKS):
        if h.cnt[r] > 0:
            add(SINGLE, order_of(r, lv), [h.by_rank[r][0]], [r])
    if h.w > 0 and h.cnt[lv] == 0:
        add(SINGLE, order_of(lv, lv), [h.wilds[0]], [lv])

    # --- pairs ---
    for r in range(13):
        if h.cnt[r] >= 2:
            add(PAIR, order_of(r, lv), h.by_rank[r][:2], [r, r])
        elif h.cnt[r] == 1 and h.w >= 1:
            add(PAIR, order_of(r, lv), [h.by_rank[r][0], h.wilds[0]], [r, r])
    if h.cnt[lv] == 0 and h.w >= 2:
        add(PAIR, order_of(lv, lv), h.wilds[:2], [lv, lv])
    for r in (SJ, BJ):
        if h.cnt[r] >= 2:
            add(PAIR, order_of(r, lv), h.by_rank[r][:2], [r, r])

    # --- triples ---
    for r in range(13):
        if h.cnt[r] >= 1 and h.cnt[r] + h.w >= 3:
            res = h.pick(r, 3, 0)
            if res:
                add(TRIPLE, order_of(r, lv), res[0], res[1])

    # --- full house (三带二) ---
    for r in range(13):
        if h.cnt[r] == 0 or h.cnt[r] + h.w < 3:
            continue
        wt = max(0, 3 - h.cnt[r])
        trip = h.pick(r, 3, 0)
        if not trip:
            continue
        for p in range(NUM_RANKS):
            if p == r:
                continue
            if p >= 13:  # joker pair attachment
                if h.cnt[p] >= 2:
                    add(FULL, order_of(r, lv), trip[0] + h.by_rank[p][:2],
                        trip[1] + [p, p])
                continue
            wp = max(0, 2 - h.cnt[p])
            if h.cnt[p] == 0 or wt + wp > h.w:
                continue
            pair_cards = h.by_rank[p][:2 - wp] + h.wilds[trip[2]:trip[2] + wp]
            add(FULL, order_of(r, lv), trip[0] + pair_cards, trip[1] + [p, p])

    # --- straights (and straight flushes) ---
    for low in range(1, 11):
        vals = list(range(low, low + 5))
        ranks = [SEQV_TO_RANK[v] for v in vals]
        need = sum(1 for r in ranks if h.cnt[r] == 0)
        if need <= h.w:
            picked, claim, wu = [], [], 0
            for r in ranks:
                if h.cnt[r] > 0:
                    picked.append(h.by_rank[r][0])
                else:
                    picked.append(h.wilds[wu]); wu += 1
                claim.append(r)
            # avoid an accidental mono-suit pick (would classify as SFLUSH)
            suit_fixed = all(rank_of(c) == cr for c, cr in zip(picked, claim))
            if suit_fixed and len(set(suit_of(c) for c in picked)) == 1:
                fixed = False
                for j, r in enumerate(ranks):
                    for alt in h.by_rank[r]:
                        if suit_of(alt) != suit_of(picked[j]):
                            picked[j] = alt
                            fixed = True
                            break
                    if fixed:
                        break
                if fixed:
                    add(STRAIGHT, low, picked, claim)
            else:
                add(STRAIGHT, low, picked, claim)
        # straight flush per suit
        for s in range(4):
            miss = [r for r in ranks if (s, r) not in h.by_suit_rank]
            if len(miss) <= h.w:
                picked, claim, wu = [], [], 0
                for r in ranks:
                    cell = h.by_suit_rank.get((s, r))
                    if cell:
                        picked.append(cell[0])
                    else:
                        picked.append(h.wilds[wu]); wu += 1
                    claim.append(r)
                add(SFLUSH, low, picked, claim)

    # --- plates (三连对) ---
    for low in range(1, 13):
        vals = list(range(low, low + 3))
        ranks = [SEQV_TO_RANK[v] for v in vals]
        need = sum(max(0, 2 - h.cnt[r]) for r in ranks)
        if need <= h.w:
            picked, claim, wu = [], [], 0
            for r in ranks:
                k = min(2, h.cnt[r])
                picked += h.by_rank[r][:k]
                take = 2 - k
                picked += h.wilds[wu:wu + take]; wu += take
                claim += [r, r]
            add(PLATE, low, picked, claim)

    # --- tubes (钢板) ---
    for low in range(1, 14):
        vals = [low, low + 1]
        ranks = [SEQV_TO_RANK[v] for v in vals]
        need = sum(max(0, 3 - h.cnt[r]) for r in ranks)
        if need <= h.w:
            picked, claim, wu = [], [], 0
            for r in ranks:
                k = min(3, h.cnt[r])
                picked += h.by_rank[r][:k]
                take = 3 - k
                picked += h.wilds[wu:wu + take]; wu += take
                claim += [r, r, r]
            add(TUBE, low, picked, claim)

    # --- bombs ---
    for r in range(13):
        if h.cnt[r] == 0:
            continue
        max_n = min(h.cnt[r] + h.w, 10)
        for n in range(4, max_n + 1):
            res = h.pick(r, n, 0)
            if res:
                add(BOMB, order_of(r, lv), res[0], res[1])

    # --- rocket ---
    if h.cnt[SJ] >= 2 and h.cnt[BJ] >= 2:
        add(ROCKET, 0, h.by_rank[SJ][:2] + h.by_rank[BJ][:2],
            [SJ, SJ, BJ, BJ])

    if lead is None or lead.type == PASS:
        return out
    legal = [m for m in out if beats(m, lead, lv)]
    return [PASS_MOVE] + legal


# ---------------------------------------------------------------------------
# classification of an observed (action, claim) pair  -> Move
# ---------------------------------------------------------------------------

def _find_seq_low(ranks, length, mult):
    """If `ranks` is exactly `length` consecutive rank groups with multiplicity
    `mult`, return lowest seq value; else None."""
    from collections import Counter
    cnt = Counter(ranks)
    if any(v != mult for v in cnt.values()) or len(cnt) != length:
        return None
    for low in range(1, 15 - length + 1):
        need = [SEQV_TO_RANK[v] for v in range(low, low + length)]
        if None in need:
            continue
        need_cnt = Counter()
        for r in need:
            need_cnt[r] += mult
        if need_cnt == cnt:
            return low
    return None


def classify_claim(action_cards, claim_cards, lv):
    """Reconstruct a Move from an observed botzone (action, claim) pair."""
    if not claim_cards:
        return PASS_MOVE
    ranks = sorted(rank_of(c) for c in claim_cards)
    n = len(ranks)
    from collections import Counter
    cnt = Counter(ranks)
    distinct = sorted(cnt)

    if n == 4 and cnt.get(SJ) == 2 and cnt.get(BJ) == 2:
        return Move(ROCKET, 0, list(action_cards), ranks)
    if len(distinct) == 1:
        r = distinct[0]
        if n == 1:
            return Move(SINGLE, order_of(r, lv), list(action_cards), ranks)
        if n == 2:
            return Move(PAIR, order_of(r, lv), list(action_cards), ranks)
        if n == 3:
            return Move(TRIPLE, order_of(r, lv), list(action_cards), ranks)
        if n >= 4:
            return Move(BOMB, order_of(r, lv), list(action_cards), ranks)
    if n == 5:
        if len(distinct) == 2 and sorted(cnt.values()) == [2, 3]:
            trip = [r for r in cnt if cnt[r] == 3][0]
            return Move(FULL, order_of(trip, lv), list(action_cards), ranks)
        low = _find_seq_low(ranks, 5, 1)
        if low is not None:
            suits = set(suit_of(c) for c in claim_cards)
            t = SFLUSH if len(suits) == 1 and -1 not in suits else STRAIGHT
            return Move(t, low, list(action_cards), ranks)
    if n == 6:
        low = _find_seq_low(ranks, 3, 2)
        if low is not None:
            return Move(PLATE, low, list(action_cards), ranks)
        low = _find_seq_low(ranks, 2, 3)
        if low is not None:
            return Move(TUBE, low, list(action_cards), ranks)
    raise ValueError("unclassifiable claim: %r" % (claim_cards,))
