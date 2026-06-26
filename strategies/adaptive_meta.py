"""
AdaptiveMeta: observe board fill rate to detect table aggressiveness,
then interpolate between MidRange (defensive table) and HighestCard (aggressive table).

Fill rate = average row length observed each round.
- Low fill rate → defensive table → MidRange style (don't trigger)
- High fill rate → aggressive table → HighestCard style (let others trigger)

Transition threshold: avg_fill = 2.5 cards/row = "neutral".
Reads ctx.cards_seen_all_rounds to infer fill rate progression.
"""

from game.card import Card
from strategies.base import Strategy, GameContext

ROW_LIMIT = 6
NEUTRAL_FILL = 2.5   # avg row length considered "normal"
SAFETY_WEIGHT = 0.25  # constant weight to avoid hard triggers


def _aggression(board: list[tuple[int, int, int]], ctx: GameContext | None) -> float:
    avg_len = sum(l for _, _, l in board) / len(board)
    # Also factor in how many cards have been seen (proxy for game pace)
    if ctx and ctx.round_number > 1:
        # More cards seen per round than expected = aggressive table
        expected_seen = (ctx.round_number - 1) * ctx.n_players
        actual_seen = len(ctx.cards_seen_all_rounds)
        pace = actual_seen / max(expected_seen, 1)
    else:
        pace = 1.0

    raw = (avg_len / NEUTRAL_FILL) * pace
    return max(0.0, min(1.0, (raw - 0.7) / 0.9))   # maps [0.7, 1.6] → [0, 1]


def _score(card: Card, board: list[tuple[int, int, int]], aggression: float) -> float:
    heads = sorted(h for h, _, _ in board)
    median_head = heads[len(heads) // 2]

    mid_score  = abs(card.value - median_head) / 104.0
    high_score = (104 - card.value) / 104.0

    below = [(i, card.value - h, pen, l) for i, (h, pen, l) in enumerate(board) if card.value > h]
    if not below:
        trigger_pen = 0.5
    elif min(below, key=lambda x: x[1])[3] == ROW_LIMIT - 1:
        trigger_pen = 1.0
    else:
        trigger_pen = 0.0

    return ((1 - aggression) * mid_score
            + aggression * high_score
            + SAFETY_WEIGHT * trigger_pen)


class AdaptiveMetaStrategy(Strategy):
    def choose_card(self, hand, board, ctx=None):
        agg = _aggression(board, ctx)
        return min(hand, key=lambda c: (_score(c, board, agg), c.value))

    def choose_row(self, hand, board, card, ctx=None):
        return min(range(len(board)), key=lambda i: board[i][1])
