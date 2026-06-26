"""Random strategy — baseline."""

import random
from game.card import Card
from strategies.base import Strategy


class RandomStrategy(Strategy):
    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)

    def choose_card(self, hand: list[Card], board: list[tuple[int, int]]) -> Card:
        return self._rng.choice(hand)

    def choose_row(self, hand: list[Card], board: list[tuple[int, int]], card: Card) -> int:
        return self._rng.randrange(len(board))
