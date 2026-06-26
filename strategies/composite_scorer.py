"""
CompositeScorer: weighted combination of 4 risk dimensions.

  D1 (w=0.35): trigger risk — am I the 6th card?
  D2 (w=0.25): row density — how full is the target row?
  D3 (w=0.20): row penalty — how costly would collecting be?
  D4 (w=0.20): card value — prefer lower cards (save highs for later)

choose_row: 60% penalty + 40% inverse-length (prefer shorter rows post-take).
"""

from game.card import Card
from strategies.base import Strategy, GameContext

W1, W2, W3, W4 = 0.35, 0.25, 0.20, 0.20
ROW_LIMIT = 6


def _score(card: Card, board: list[tuple[int, int, int]]) -> float:
    below = [(i, card.value - h, pen, l) for i, (h, pen, l) in enumerate(board) if card.value > h]
    if not below:
        return 9000 + min(pen for _, pen, _ in board)

    _, _, pen, length = min(below, key=lambda x: x[1])

    d1 = 1.0 if length == ROW_LIMIT - 1 else (length / (ROW_LIMIT - 1)) * 0.3
    d2 = length / (ROW_LIMIT - 1)
    d3 = min(pen / 20.0, 1.0)
    d4 = card.value / 104.0

    return W1 * d1 + W2 * d2 + W3 * d3 + W4 * d4


class CompositeScorerStrategy(Strategy):
    def choose_card(self, hand, board, ctx=None):
        return min(hand, key=lambda c: (_score(c, board), c.value))

    def choose_row(self, hand, board, card, ctx=None):
        return min(range(len(board)), key=lambda i: 0.6 * board[i][1] + 0.4 * (5 - board[i][2]))
