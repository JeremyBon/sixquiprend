"""Game engine: one full game of 6 qui prend."""

from __future__ import annotations
from dataclasses import dataclass, field
from game.card import Card
from game.board import Board
from game.deck import make_deck

HAND_SIZE = 10


@dataclass
class PlayerState:
    name: str
    hand: list[Card] = field(default_factory=list)
    penalties: int = 0


@dataclass
class GameResult:
    scores: dict[str, int]      # player_name -> total penalty points
    history: list[dict]         # one entry per round


class Game:
    def __init__(self, player_names: list[str], strategies: dict, seed: int | None = None):
        """
        strategies: {player_name: StrategyInstance}
        StrategyInstance must implement:
          - choose_card(hand, board_snapshot) -> Card
          - choose_row(hand, board_snapshot, card) -> int  (when card < all heads)
        """
        self.player_names = player_names
        self.strategies = strategies
        self.seed = seed
        self._rng_seed = seed

    def run(self) -> GameResult:
        deck = make_deck(self.seed)
        players = [PlayerState(name=n) for n in self.player_names]

        # deal 10 cards each
        for i, p in enumerate(players):
            p.hand = deck[i * HAND_SIZE: (i + 1) * HAND_SIZE]
        deck = deck[len(players) * HAND_SIZE:]

        # 4 starter cards for board
        board = Board(deck[:4])
        deck = deck[4:]

        history = []

        for _round in range(HAND_SIZE):
            round_log = {"round": _round + 1, "plays": []}
            snapshot = board.snapshot()

            # each player picks a card
            choices: list[tuple[PlayerState, Card]] = []
            for p in players:
                strat = self.strategies[p.name]
                card = strat.choose_card(list(p.hand), snapshot)
                p.hand.remove(card)
                choices.append((p, card))

            # resolve in ascending card order
            choices.sort(key=lambda x: x[1].value)

            for player, card in choices:
                snapshot = board.snapshot()
                row_idx = board.target_row(card)

                if row_idx is None:
                    # card smaller than all heads — must pick a row
                    strat = self.strategies[player.name]
                    row_idx = strat.choose_row(list(player.hand), snapshot, card)
                    taken = board.force_take(row_idx, card)
                else:
                    taken = board.place(card, row_idx)

                penalty = sum(c.penalty for c in taken) if taken else 0
                player.penalties += penalty
                round_log["plays"].append({
                    "player": player.name,
                    "card": card.value,
                    "row": row_idx,
                    "took": [c.value for c in taken] if taken else [],
                    "penalty": penalty,
                })

            history.append(round_log)

        return GameResult(
            scores={p.name: p.penalties for p in players},
            history=history,
        )
