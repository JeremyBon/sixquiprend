"""Deck: 104 cards, shuffled."""

import random
from game.card import Card


def make_deck(seed: int | None = None) -> list[Card]:
    deck = [Card(v) for v in range(1, 105)]
    rng = random.Random(seed)
    rng.shuffle(deck)
    return deck
