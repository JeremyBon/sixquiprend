"""
Cautious: Greedy + avoids filling the last slot of any row unless no other choice.

Score per card:
  - Fills row (length==5): cost = row_penalty + 1000 (heavy penalty, avoid if possible)
  - No row fits (forced take): cost = min_row_penalty + 500
  - Safe placement: cost = 0

Tiebreak: lowest card value.
When forced to take: pick cheapest row.
"""

from game.card import Card
from strategies.base import Strategy

ROW_LIMIT = 6
FILL_WEIGHT = 1000
FORCED_WEIGHT = 500


def _card_cost(card: Card, board: list[tuple[int, int, int]]) -> float:
    below = [
        (i, card.value - head, pen, length)
        for i, (head, pen, length) in enumerate(board)
        if card.value > head
    ]
    if not below:
        min_pen = min(pen for _, pen, _ in board)
        return FORCED_WEIGHT + min_pen

    _, _, pen, length = min(below, key=lambda x: x[1])
    if length == ROW_LIMIT - 1:
        return FILL_WEIGHT + pen
    return 0.0


class CautiousStrategy(Strategy):
    def choose_card(self, hand, board, ctx=None):
        return min(hand, key=lambda c: (_card_cost(c, board), c.value))

    def choose_row(self, hand, board, card, ctx=None):
        return min(range(len(board)), key=lambda i: board[i][1])
