"""FableDan: GuanDan AI trained via DMC self-play with a tiny transformer.

Botzone card encoding (used internally everywhere):
  card id 0..107.  Let b = id % 54.
    b < 52 : rank index r = b // 4   (0=A, 1=2, ..., 9=10, 10=J, 11=Q, 12=K)
             suit s = b % 4          (0=hearts, 1=diamonds, 2=spades, 3=clubs)
    b == 52: small joker (rank index 13)
    b == 53: big joker   (rank index 14)
"""

__version__ = "0.1.0"
