"""
PenaltyDodger: minimise expected cost = P(trigger) * row_penalty.

P(trigger) proxy = 1 / slots_remaining  (fewer slots = more likely someone fills it).
If forced: cost = min_row_penalty + 200.
Tiebreak: lowest penalty on the card itself (avoid high-bull cards).
choose_row: always take cheapest row.
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
        return float(min(pen for _, pen, _ in board)) + 200.0

    _, _, pen, length = min(below, key=lambda x: x[1])
    slots_left = (ROW_LIMIT - 1) - length
    prob_trigger = 1.0 / max(slots_left, 1)
    return prob_trigger * pen


class PenaltyDodgerStrategy(Strategy):
    def choose_card(self, hand: list[Card], board: list[tuple[int, int, int]]) -> Card:
        return min(hand, key=lambda c: (_card_cost(c, board), c.penalty, c.value))

    def choose_row(self, hand: list[Card], board: list[tuple[int, int, int]], card: Card) -> int:
        return min(range(len(board)), key=lambda i: board[i][1])
