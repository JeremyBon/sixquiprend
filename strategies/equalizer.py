"""
Equalizer: keep board balanced — avoid piling onto already-crowded rows.

cost = (row.length - avg_length) * 10 + fill_penalty
  fill_penalty = max(0, row.length - 3) * row.penalty * 0.5

choose_row: take row whose length is closest to avg_length — preserve balance.
"""

from game.card import Card
from strategies.base import Strategy


def _card_cost(card: Card, board: list[tuple[int, int, int]]) -> float:
    avg_length = sum(l for _, _, l in board) / len(board)
    below = [
        (i, card.value - head, pen, length)
        for i, (head, pen, length) in enumerate(board)
        if card.value > head
    ]
    if not below:
        return 9000.0

    _, _, pen, length = min(below, key=lambda x: x[1])
    deviation = length - avg_length
    fill_penalty = max(0, length - 3) * pen * 0.5
    return deviation * 10 + fill_penalty


class EqualizerStrategy(Strategy):
    def choose_card(self, hand, board, ctx=None):
        return min(hand, key=lambda c: (_card_cost(c, board), c.value))

    def choose_row(self, hand, board, card, ctx=None):
        avg_length = sum(l for _, _, l in board) / len(board)
        return min(range(len(board)), key=lambda i: abs(board[i][2] - avg_length))
