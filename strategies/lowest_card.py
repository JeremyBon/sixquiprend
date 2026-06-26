"""LowestCard: always play the lowest card in hand; take cheapest row when forced."""

from game.card import Card
from strategies.base import Strategy


class LowestCardStrategy(Strategy):
    def choose_card(self, hand, board, ctx=None):
        return min(hand)

    def choose_row(self, hand, board, card, ctx=None):
        return min(range(len(board)), key=lambda i: board[i][1])
