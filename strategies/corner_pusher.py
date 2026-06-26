"""
CornerPusher: externalise trigger cost onto other players.

Card types (priority A > D > C > B):
  A: lands on row length <= 3  (safe)
  D: lands on row length == 4  (risky but manageable)
  C: no row fits               (forced take, cheap row)
  B: lands on row length == 5  (we trigger — avoid)

Within type A: prefer card that pushes head highest (card.value max)
  → forces opponents with slightly-higher cards onto less dangerous rows
Within others: lowest card value.

choose_row: cheapest penalty; tiebreak on highest head_value (hard for others to land on).
"""

from game.card import Card
from strategies.base import Strategy

ROW_LIMIT = 6


def _classify(card: Card, board: list[tuple[int, int, int]]) -> tuple:
    below = [
        (i, card.value - head, pen, length)
        for i, (head, pen, length) in enumerate(board)
        if card.value > head
    ]
    if not below:
        return (2, card.value)   # C: forced take — mid priority

    _, _, pen, length = min(below, key=lambda x: x[1])
    if length <= 3:
        return (0, -card.value)  # A: safe — prefer highest card to push head up
    if length == 4:
        return (1, pen)          # D: risky — prefer lower penalty row
    # length == 5
    return (3, pen)              # B: trigger — worst, prefer lower penalty


class CornerPusherStrategy(Strategy):
    def choose_card(self, hand, board, ctx=None):
        return min(hand, key=lambda c: _classify(c, board))

    def choose_row(self, hand, board, card, ctx=None):
        min_pen = min(p for _, p, _ in board)
        candidates = [i for i, (_, p, _) in enumerate(board) if p <= min_pen + 2]
        # Among cheap rows, prefer highest head (harder for opponents to land on)
        return max(candidates, key=lambda i: board[i][0])
