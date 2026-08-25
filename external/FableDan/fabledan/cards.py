# -*- coding: utf-8 -*-
"""Card utilities. Botzone ids 0..107, rank indices 0..14 (A..K, SJ, BJ)."""

NUM_CARDS = 108
SJ, BJ = 13, 14          # rank indices of small / big joker
NUM_RANKS = 15           # 13 normal ranks + 2 jokers
RANK_NAMES = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "sj", "BJ"]
SUIT_NAMES = ["h", "d", "s", "c"]


def rank_of(card: int) -> int:
    b = card % 54
    if b >= 52:
        return SJ if b == 52 else BJ
    return b // 4


def suit_of(card: int) -> int:
    """0=h 1=d 2=s 3=c, jokers -> -1."""
    b = card % 54
    return -1 if b >= 52 else b % 4


def card_name(card: int) -> str:
    r = rank_of(card)
    if r >= 13:
        return RANK_NAMES[r]
    return SUIT_NAMES[suit_of(card)] + RANK_NAMES[r]


def level_rank(level_str: str) -> int:
    """Botzone level string ('2'..'10','J','Q','K','A') -> rank index 0..12."""
    return RANK_NAMES.index(str(level_str))


def is_wildcard(card: int, lv: int) -> bool:
    """Heart level card (配子)."""
    return rank_of(card) == lv and suit_of(card) == 0


def order_of(rank: int, lv: int) -> int:
    """Comparison order for singles/pairs/triples/bombs under level `lv`.

    Natural ascending 2,3,...,K,A with level card pulled out and placed
    above A; jokers on top.  Returns 0..14 (higher = bigger).
    A natural order: 2..K -> 0..11 skipping positions, easier to build a table.
    """
    return _ORDER_TABLE[lv][rank]


def _build_order_tables():
    tables = []
    for lv in range(13):
        seq = [r for r in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 0] if r != lv]
        seq.append(lv)        # level card just below jokers
        seq += [SJ, BJ]
        t = [0] * NUM_RANKS
        for pos, r in enumerate(seq):
            t[r] = pos
        tables.append(t)
    return tables


_ORDER_TABLE = _build_order_tables()

# sequence value for straights/plates/tubes: A=1 or 14, 2=2 ... K=13.
# We index sequences by their LOWEST seq value.
# rank index -> natural seq value(s)
def seq_values(rank: int):
    if rank == 0:
        return (1, 14)
    return (rank + 1,)


# seq value -> rank index (1..14)
SEQV_TO_RANK = [None] + [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 0]


def sort_cards(cards, lv: int):
    return sorted(cards, key=lambda c: (order_of(rank_of(c), lv), c))
