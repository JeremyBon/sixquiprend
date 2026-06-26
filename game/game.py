"""Game engine: one full game of 6 qui prend."""

from __future__ import annotations
from dataclasses import dataclass, field
from game.card import Card
from game.board import Board
from game.deck import make_deck
from strategies.base import GameContext

HAND_SIZE = 10


@dataclass
class PlayerState:
    name: str
    hand: list[Card] = field(default_factory=list)
    penalties: int = 0


@dataclass
class GameResult:
    scores: dict[str, int]
    history: list[dict]


class Game:
    def __init__(self, player_names: list[str], strategies: dict, seed: int | None = None):
        self.player_names = player_names
        self.strategies = strategies
        self.seed = seed

    def run(self) -> GameResult:
        deck = make_deck(self.seed)
        players = [PlayerState(name=n) for n in self.player_names]

        for i, p in enumerate(players):
            p.hand = deck[i * HAND_SIZE: (i + 1) * HAND_SIZE]
        deck = deck[len(players) * HAND_SIZE:]

        board = Board(deck[:4])

        history = []
        cards_seen: list[int] = []  # all cards played in previous rounds

        for round_num in range(HAND_SIZE):
            round_log = {"round": round_num + 1, "plays": []}
            snapshot = board.snapshot()
            cards_played_this_round: list[int] = []

            choices: list[tuple[PlayerState, Card]] = []
            for p in players:
                strat = self.strategies[p.name]
                ctx = GameContext(
                    round_number=round_num + 1,
                    cards_played_this_round=list(cards_played_this_round),
                    cards_seen_all_rounds=list(cards_seen),
                    n_players=len(players),
                    rounds_remaining=HAND_SIZE - round_num,
                )
                card = strat.choose_card(list(p.hand), snapshot, ctx)
                p.hand.remove(card)
                choices.append((p, card))

            choices.sort(key=lambda x: x[1].value)

            for player, card in choices:
                snapshot = board.snapshot()
                row_idx = board.target_row(card)

                ctx = GameContext(
                    round_number=round_num + 1,
                    cards_played_this_round=list(cards_played_this_round),
                    cards_seen_all_rounds=list(cards_seen),
                    n_players=len(players),
                    rounds_remaining=HAND_SIZE - round_num,
                )

                if row_idx is None:
                    strat = self.strategies[player.name]
                    row_idx = strat.choose_row(list(player.hand), snapshot, card, ctx)
                    taken = board.force_take(row_idx, card)
                else:
                    taken = board.place(card, row_idx)

                penalty = sum(c.penalty for c in taken) if taken else 0
                player.penalties += penalty
                cards_played_this_round.append(card.value)
                round_log["plays"].append({
                    "player": player.name,
                    "card": card.value,
                    "row": row_idx,
                    "took": [c.value for c in taken] if taken else [],
                    "penalty": penalty,
                })

            cards_seen.extend(cards_played_this_round)
            history.append(round_log)

        return GameResult(
            scores={p.name: p.penalties for p in players},
            history=history,
        )
