"""Card representation for 6 qui prend."""

PENALTIES = {
    55: 7,
    11: 5, 22: 5, 33: 5, 44: 5, 66: 5, 77: 5, 88: 5, 99: 5,
}

def _compute_penalty(value: int) -> int:
    if value in PENALTIES:
        return PENALTIES[value]
    if value % 10 == 0:
        return 3
    if value % 5 == 0:
        return 2
    return 1


class Card:
    __slots__ = ("value", "penalty")

    def __init__(self, value: int):
        self.value = value
        self.penalty = _compute_penalty(value)

    def __repr__(self):
        return f"Card({self.value}, -{self.penalty})"

    def __lt__(self, other):
        return self.value < other.value

    def __le__(self, other):
        return self.value <= other.value

    def __eq__(self, other):
        return self.value == other.value

    def __hash__(self):
        return hash(self.value)
