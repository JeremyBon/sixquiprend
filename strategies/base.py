"""Base class for all strategies."""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from game.card import Card


@dataclass
class GameContext:
    """Optional rich context passed to strategies that opt in."""
    round_number: int          # 1-10
    cards_played_this_round: list[int]   # values already resolved this round (before our turn)
    cards_seen_all_rounds: list[int]     # all card values played so far (previous rounds)
    n_players: int
    rounds_remaining: int      # rounds left including current


class Strategy(ABC):
    @abstractmethod
    def choose_card(
        self,
        hand: list[Card],
        board: list[tuple[int, int, int]],
        ctx: GameContext | None = None,
    ) -> Card:
        """Pick a card to play. board = [(head_value, row_penalty, row_length), ...]"""

    @abstractmethod
    def choose_row(
        self,
        hand: list[Card],
        board: list[tuple[int, int, int]],
        card: Card,
        ctx: GameContext | None = None,
    ) -> int:
        """Card is smaller than all heads — pick which row to take."""
