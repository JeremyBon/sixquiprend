"""
ThreatAssessor: model rows as "ticking bombs" with explosion probability.

For each card, compute expected cost = P(row fills before end) * row_penalty.
P(fill) = min(1, expected_fills / slots_needed)
  where expected_fills = p_per_round * rounds_remaining
  and   p_per_round = 0.35 (empirical: ~2 cards in any gap per round at 6 players)

choose_row: defuse most urgent bomb = row with highest penalty-per-remaining-slot.
"""

from game.card import Card
from strategies.base import Strategy, GameContext

ROW_LIMIT = 6
P_PER_ROUND = 0.35


def _explosion_risk(length: int, rounds_left: int) -> float:
    slots_needed = (ROW_LIMIT - 1) - length
    if slots_needed <= 0:
        return 1.0
    if rounds_left < slots_needed:
        return 0.0
    expected_fills = P_PER_ROUND * rounds_left
    return min(1.0, expected_fills / slots_needed)


def _score(card: Card, board: list[tuple[int, int, int]], rounds_left: int) -> float:
    below = [(i, card.value - h, pen, l) for i, (h, pen, l) in enumerate(board) if card.value > h]

    if not below:
        return min(pen for _, pen, _ in board) * 0.8 + 150

    _, _, pen, length = min(below, key=lambda x: x[1])
    risk = _explosion_risk(length, rounds_left)

    multiplier = {4: 1.5, 3: 0.5, 2: 0.3}.get(length, 0.1)
    return pen * risk * multiplier


class ThreatAssessorStrategy(Strategy):
    def choose_card(self, hand, board, ctx=None):
        rounds_left = ctx.rounds_remaining if ctx else len(hand)
        return min(hand, key=lambda c: (_score(c, board, rounds_left), c.value))

    def choose_row(self, hand, board, card, ctx=None):
        # Defuse least urgent bomb (taking it resets it to length=1)
        return min(range(len(board)), key=lambda i: board[i][1] / max((ROW_LIMIT - 1) - board[i][2], 0.5))
