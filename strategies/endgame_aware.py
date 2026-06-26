"""
EndgameAware: adapt play style based on rounds remaining.

Early game (rounds 1-4): avoid risks, play low cards — many opponent cards still in play.
Mid game (rounds 5-7): balanced — Greedy-like.
Late game (rounds 8-10): play high cards freely — few cards left, rows won't fill easily.

Transition is smooth via game_progress scalar [0, 1].

choose_row late-game: take row with highest head (hard for surviving opponents to land on).
"""

from game.card import Card
from strategies.base import Strategy, GameContext

ROW_LIMIT = 6
HAND_SIZE = 10


def _score(card: Card, board: list[tuple[int, int, int]], game_progress: float) -> float:
    below = [(i, card.value - h, pen, l) for i, (h, pen, l) in enumerate(board) if card.value > h]

    if not below:
        base = min(pen for _, pen, _ in board) + 200
        return base * (1 - game_progress * 0.4)

    _, _, pen, length = min(below, key=lambda x: x[1])

    if length == ROW_LIMIT - 1:
        return pen * (1 - game_progress * 0.5)

    # Early: reward low cards; late: reward high cards (safe to burn)
    low_bias   = (1 - game_progress) * (1 - card.value / 104.0) * 10
    high_bias  = game_progress       * (card.value / 104.0) * 10
    return -(low_bias + high_bias)   # negative = preferred


class EndgameAwareStrategy(Strategy):
    def choose_card(self, hand, board, ctx=None):
        rounds_remaining = ctx.rounds_remaining if ctx else len(hand)
        progress = 1 - (rounds_remaining / HAND_SIZE)
        return min(hand, key=lambda c: (_score(c, board, progress), c.value))

    def choose_row(self, hand, board, card, ctx=None):
        rounds_remaining = ctx.rounds_remaining if ctx else len(hand)
        if rounds_remaining <= 3:
            # Late: leave highest head on board — hard for opponents to land
            return max(range(len(board)), key=lambda i: board[i][0])
        return min(range(len(board)), key=lambda i: board[i][1])
