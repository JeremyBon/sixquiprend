"""
GapHunter: seek cards that land in wide gaps on rows with low fill risk.

cost = fill_risk * 100 - gap * 0.5
  fill_risk = row.length / 5      (0.2 → 1.0)
  gap       = card.value - head   (wider = safer, others will fill before us)

choose_row: minimise penalty-per-remaining-slot (avoid dense rows near trigger).
"""

from game.card import Card
from strategies.base import Strategy

ROW_LIMIT = 6


def _card_cost(card: Card, board: list[tuple[int, int, int]]) -> float:
    below = [
        (i, card.value - head, pen, length)
        for i, (head, pen, length) in enumerate(board)
        if card.value > head
    ]
    if not below:
        return float(min(pen for _, pen, _ in board)) + 500.0

    i, gap, pen, length = min(below, key=lambda x: x[1])
    fill_risk = length / (ROW_LIMIT - 1)
    return fill_risk * 100 - gap * 0.5


class GapHunterStrategy(Strategy):
    def choose_card(self, hand, board, ctx=None):
        return min(hand, key=lambda c: (_card_cost(c, board), c.value))

    def choose_row(self, hand, board, card, ctx=None):
        # minimise penalty / remaining slots — avoid dense rows close to exploding
        def score(i):
            _, pen, length = board[i]
            remaining = ROW_LIMIT - 1 - length
            return pen / max(remaining, 0.5)
        return min(range(len(board)), key=score)
