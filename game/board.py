"""Board: 4 rows, placement logic."""

from __future__ import annotations
from dataclasses import dataclass, field
from game.card import Card

NUM_ROWS = 4
ROW_LIMIT = 6  # 6th card triggers pickup


@dataclass
class Row:
    cards: list[Card] = field(default_factory=list)

    @property
    def head(self) -> Card:
        return self.cards[-1]

    @property
    def penalty(self) -> int:
        return sum(c.penalty for c in self.cards)

    def __len__(self):
        return len(self.cards)


class Board:
    def __init__(self, starter_cards: list[Card]):
        assert len(starter_cards) == NUM_ROWS
        self.rows: list[Row] = [Row([c]) for c in starter_cards]

    def target_row(self, card: Card) -> int | None:
        """Index of the row whose head is the closest value below card. None if none."""
        best_idx = None
        best_diff = float("inf")
        for i, row in enumerate(self.rows):
            diff = card.value - row.head.value
            if 0 < diff < best_diff:
                best_diff = diff
                best_idx = i
        return best_idx

    def place(self, card: Card, row_idx: int) -> list[Card] | None:
        """
        Place card on row_idx.
        Returns taken cards if row was full (6th card), else None.
        """
        row = self.rows[row_idx]
        if len(row) == ROW_LIMIT - 1:
            taken = list(row.cards)
            row.cards = [card]
            return taken
        row.cards.append(card)
        return None

    def force_take(self, row_idx: int, new_card: Card) -> list[Card]:
        """Player chose a row to take (card smaller than all heads)."""
        row = self.rows[row_idx]
        taken = list(row.cards)
        row.cards = [new_card]
        return taken

    def snapshot(self) -> list[tuple[int, int, int]]:
        """(head_value, row_penalty, row_length) per row — for strategies."""
        return [(r.head.value, r.penalty, len(r)) for r in self.rows]
