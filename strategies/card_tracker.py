"""
CardTracker: infer opponent card distribution from cards already played.

Remaining opponent cards = all 104 - our hand - cards seen this game.
For each card we play:
  - Count opponent cards in the gap (head_value, card.value) on target row
  - More opponent cards in gap = more likely row fills before us = safer landing
  - Paradox: if we play below a gap with many opponents, THEY collect, not us

Risk formula:
  slots_left = 5 - row.length
  opponents_in_gap = |{c in remaining_opponents: head < c < card.value}|
  fills_before_us = min(opponents_in_gap, slots_left - 1)
  effective_slots_after_fills = slots_left - fills_before_us
  if effective_slots_after_fills <= 0: cost = 0   (someone else collects before us)
  elif effective_slots_after_fills == 1: cost = pen (we're the 6th)
  else: cost = 0

choose_row: cheapest row (classic damage control).
"""

from game.card import Card
from strategies.base import Strategy, GameContext

ROW_LIMIT = 6


def _score(card: Card, board: list[tuple[int, int, int]], remaining_opponents: set[int]) -> float:
    below = [(i, card.value - h, pen, l) for i, (h, pen, l) in enumerate(board) if card.value > h]
    if not below:
        return float(min(pen for _, pen, _ in board)) + 300

    i, _, pen, length = min(below, key=lambda x: x[1])
    head = board[i][0]
    slots_left = (ROW_LIMIT - 1) - length

    opponents_in_gap = sum(1 for c in remaining_opponents if head < c < card.value)
    fills_before_us = min(opponents_in_gap, slots_left - 1)
    effective = slots_left - fills_before_us

    if effective <= 0:
        return 0.0    # opponent(s) will collect, not us
    if effective == 1:
        return float(pen)   # we trigger
    return 0.0


class CardTrackerStrategy(Strategy):
    def __init__(self):
        self._seen: set[int] = set()

    def _remaining_opponents(self, hand: list[Card], ctx: GameContext | None) -> set[int]:
        all_cards = set(range(1, 105))
        my_cards = {c.value for c in hand}
        seen = set(ctx.cards_seen_all_rounds) if ctx else self._seen
        return all_cards - my_cards - seen

    def choose_card(self, hand, board, ctx=None):
        remaining = self._remaining_opponents(hand, ctx)
        return min(hand, key=lambda c: (_score(c, board, remaining), c.value))

    def choose_row(self, hand, board, card, ctx=None):
        return min(range(len(board)), key=lambda i: board[i][1])
