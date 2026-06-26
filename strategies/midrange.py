"""
MidRange: play the card closest to the median of all row heads.

Intuition: median cards are least likely to either (a) trigger forced takes
(too low) or (b) jump over many rows and land on a dangerous full row.

Tiebreak: lowest card value.
When forced to take: pick cheapest row.
"""

from game.card import Card
from strategies.base import Strategy


class MidRangeStrategy(Strategy):
    def choose_card(self, hand: list[Card], board: list[tuple[int, int, int]]) -> Card:
        heads = sorted(h for h, _, _ in board)
        median = heads[len(heads) // 2]
        return min(hand, key=lambda c: (abs(c.value - median), c.value))

    def choose_row(self, hand: list[Card], board: list[tuple[int, int, int]], card: Card) -> int:
        return min(range(len(board)), key=lambda i: board[i][1])
