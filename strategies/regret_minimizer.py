"""
RegretMinimizer: minimax-regret card selection.

For each card:
  worst_case = max penalty we could receive in worst adversarial scenario
  best_case  = min penalty (lucky case: no one else lands on our row)
  regret     = worst_case - best_case  (predictability spread)

Pick card with lowest worst_case; tiebreak by lowest regret (most predictable).

Intuition: don't gamble. Even if expected value is low, avoid cards with catastrophic
worst cases. This is especially valuable in late game where one bad draw ends you.

choose_row: standard min-penalty.
"""

from game.card import Card
from strategies.base import Strategy, GameContext

ROW_LIMIT = 6


def _worst_case(card: Card, board: list[tuple[int, int, int]]) -> float:
    below = [(i, card.value - h, pen, l) for i, (h, pen, l) in enumerate(board) if card.value > h]
    if not below:
        # Forced take — worst: most expensive row
        return float(max(pen for _, pen, _ in board))
    _, _, pen, length = min(below, key=lambda x: x[1])
    # Worst case: row fills to 5 before us → we trigger
    return float(pen)


def _best_case(card: Card, board: list[tuple[int, int, int]]) -> float:
    below = [(i, card.value - h, pen, l) for i, (h, pen, l) in enumerate(board) if card.value > h]
    if not below:
        # Forced take — best: cheapest row
        return float(min(pen for _, pen, _ in board))
    _, _, pen, length = min(below, key=lambda x: x[1])
    if length == ROW_LIMIT - 1:
        return float(pen)   # unavoidable trigger even in best case
    return 0.0


class RegretMinimizerStrategy(Strategy):
    def choose_card(self, hand, board, ctx=None):
        def key(c):
            wc = _worst_case(c, board)
            regret = wc - _best_case(c, board)
            return (wc, regret, c.value)
        return min(hand, key=key)

    def choose_row(self, hand, board, card, ctx=None):
        return min(range(len(board)), key=lambda i: board[i][1])
