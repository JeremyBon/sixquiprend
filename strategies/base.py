"""Base class for all strategies."""

from abc import ABC, abstractmethod
from game.card import Card


class Strategy(ABC):
    @abstractmethod
    def choose_card(self, hand: list[Card], board: list[tuple[int, int]]) -> Card:
        """Pick a card to play. board = [(head_value, row_penalty), ...]"""

    @abstractmethod
    def choose_row(self, hand: list[Card], board: list[tuple[int, int]], card: Card) -> int:
        """Card is smaller than all heads — pick which row to take."""
