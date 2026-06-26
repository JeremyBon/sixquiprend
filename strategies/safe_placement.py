"""
SafePlacement: pick the card that lands on the row with fewest cards remaining
before triggering a collection (i.e., maximizes distance from row limit).

Score per card = length_of_target_row  (lower = safer, more room left)
If no row fits: forced take cost = 9999.
Tiebreak: lowest card value.
When forced: pick cheapest row.
"""

from game.card import Card
from strategies.base import Strategy

ROW_LIMIT = 6


def _placement_score(card: Card, board: list[tuple[int, int, int]]) -> float:
    below = [
        (i, card.value - head, pen, length)
        for i, (head, pen, length) in enumerate(board)
        if card.value > head
    ]
    if not below:
        return 9999.0

    _, _, _, length = min(below, key=lambda x: x[1])
    return float(length)  # smaller = row has more space


class SafePlacementStrategy(Strategy):
    def choose_card(self, hand, board, ctx=None):
        return min(hand, key=lambda c: (_placement_score(c, board), c.value))

    def choose_row(self, hand, board, card, ctx=None):
        return min(range(len(board)), key=lambda i: board[i][1])
