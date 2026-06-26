"""
Greedy: pick the card that minimizes immediate expected penalty.

For each card in hand:
  - If no row can receive it (card < all heads):
      cost = min row penalty across all rows  (forced take, pick cheapest)
  - Else: find target row (closest head below card)
      * If row already has 5 cards: cost = row_penalty (we'd collect it)
      * Else: cost = 0  (safe placement)

Play card with lowest cost. Tiebreak: lowest card value (keep high cards for later).
When forced to take a row: pick the one with fewest penalty points.
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
        return float(min(pen for _, pen, _ in board))

    _, _, pen, length = min(below, key=lambda x: x[1])
    if length == ROW_LIMIT - 1:
        return float(pen)
    return 0.0


class GreedyStrategy(Strategy):
    def choose_card(self, hand: list[Card], board: list[tuple[int, int, int]]) -> Card:
        return min(hand, key=lambda c: (_card_cost(c, board), c.value))

    def choose_row(self, hand: list[Card], board: list[tuple[int, int, int]], card: Card) -> int:
        return min(range(len(board)), key=lambda i: board[i][1])
