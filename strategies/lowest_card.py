"""LowestCard: always play the lowest card in hand; take cheapest row when forced."""

from game.card import Card
from strategies.base import Strategy


class LowestCardStrategy(Strategy):
    def choose_card(self, hand: list[Card], board: list[tuple[int, int, int]]) -> Card:
        return min(hand)

    def choose_row(self, hand: list[Card], board: list[tuple[int, int, int]], card: Card) -> int:
        return min(range(len(board)), key=lambda i: board[i][1])
