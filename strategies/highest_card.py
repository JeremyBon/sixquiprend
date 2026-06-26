"""HighestCard: always play the highest card in hand; take cheapest row when forced."""

from game.card import Card
from strategies.base import Strategy


class HighestCardStrategy(Strategy):
    def choose_card(self, hand, board, ctx=None):
        return max(hand)

    def choose_row(self, hand, board, card, ctx=None):
        return min(range(len(board)), key=lambda i: board[i][1])
