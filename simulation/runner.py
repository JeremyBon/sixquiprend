"""Tournament runner: N games, aggregated stats."""

from __future__ import annotations
import statistics
from dataclasses import dataclass, field
from game.game import Game, GameResult


@dataclass
class TournamentResult:
    strategy_names: list[str]
    n_games: int
    scores: dict[str, list[int]] = field(default_factory=dict)   # strat -> [score per game]

    def summary(self) -> dict[str, dict]:
        out = {}
        for name, s in self.scores.items():
            out[name] = {
                "mean": round(statistics.mean(s), 2),
                "median": statistics.median(s),
                "stdev": round(statistics.stdev(s), 2) if len(s) > 1 else 0,
                "min": min(s),
                "max": max(s),
                "wins": sum(
                    1 for i in range(self.n_games)
                    if s[i] == min(self.scores[n][i] for n in self.strategy_names)
                ),
            }
        return out

    def print_summary(self):
        summary = self.summary()
        print(f"\n{'='*55}")
        print(f"  Tournament: {self.n_games} games, {len(self.strategy_names)} players")
        print(f"{'='*55}")
        header = f"{'Strategy':<22} {'Mean':>6} {'Median':>7} {'Stdev':>6} {'Min':>5} {'Max':>5} {'Wins':>5}"
        print(header)
        print("-" * 55)
        for name in sorted(summary, key=lambda n: summary[n]["mean"]):
            s = summary[name]
            print(
                f"{name:<22} {s['mean']:>6.1f} {s['median']:>7.1f} "
                f"{s['stdev']:>6.1f} {s['min']:>5} {s['max']:>5} {s['wins']:>5}"
            )
        print(f"{'='*55}\n")


def run_tournament(
    strategy_factories: dict[str, callable],
    n_games: int = 1000,
    base_seed: int = 42,
) -> TournamentResult:
    """
    strategy_factories: {name: callable() -> Strategy}
    Each game uses a fresh strategy instance + deterministic seed.
    """
    player_names = list(strategy_factories.keys())
    result = TournamentResult(strategy_names=player_names, n_games=n_games)
    result.scores = {n: [] for n in player_names}

    for i in range(n_games):
        seed = base_seed + i
        strategies = {name: factory() for name, factory in strategy_factories.items()}
        game = Game(player_names, strategies, seed=seed)
        gr: GameResult = game.run()
        for name in player_names:
            result.scores[name].append(gr.scores[name])

    return result
