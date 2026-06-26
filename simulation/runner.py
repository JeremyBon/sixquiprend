"""Tournament runner: N games, aggregated stats. Parallel via multiprocessing."""

from __future__ import annotations
import statistics
from dataclasses import dataclass, field
from multiprocessing import Pool, cpu_count
from game.game import Game


@dataclass
class TournamentResult:
    strategy_names: list[str]
    n_games: int
    scores: dict[str, list[int]] = field(default_factory=dict)

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
        print(f"{'Strategy':<22} {'Mean':>6} {'Median':>7} {'Stdev':>6} {'Min':>5} {'Max':>5} {'Wins':>5}")
        print("-" * 55)
        for name in sorted(summary, key=lambda n: summary[n]["mean"]):
            s = summary[name]
            print(
                f"{name:<22} {s['mean']:>6.1f} {s['median']:>7.1f} "
                f"{s['stdev']:>6.1f} {s['min']:>5} {s['max']:>5} {s['wins']:>5}"
            )
        print(f"{'='*55}\n")


def _run_batch(args: tuple) -> list[dict[str, int]]:
    """Run a batch of games in a single worker process."""
    seeds, player_names, class_paths = args

    # Reconstruct classes from module path (picklable)
    import importlib
    factories = {}
    for name, (module_path, class_name) in zip(player_names, class_paths):
        mod = importlib.import_module(module_path)
        factories[name] = getattr(mod, class_name)

    results = []
    for seed in seeds:
        strategies = {name: cls() for name, cls in factories.items()}
        game = Game(player_names, strategies, seed=seed)
        results.append(game.run().scores)
    return results


def run_tournament(
    strategy_factories: dict[str, type],
    n_games: int = 1000,
    base_seed: int = 42,
    workers: int | None = None,
) -> TournamentResult:
    """
    strategy_factories: {player_name: StrategyClass}
    Classes must be importable (top-level, not lambdas).
    """
    player_names = list(strategy_factories.keys())
    # Serialize class references as (module, classname) for cross-process import
    class_paths = [
        (cls.__module__, cls.__name__)
        for cls in strategy_factories.values()
    ]

    n_workers = workers or max(1, cpu_count() - 1)
    seeds = list(range(base_seed, base_seed + n_games))

    # Split seeds into n_workers batches
    batch_size = max(1, (n_games + n_workers - 1) // n_workers)
    batches = [
        (seeds[i:i + batch_size], player_names, class_paths)
        for i in range(0, len(seeds), batch_size)
    ]

    result = TournamentResult(strategy_names=player_names, n_games=n_games)
    result.scores = {n: [] for n in player_names}

    with Pool(processes=n_workers) as pool:
        for batch_results in pool.map(_run_batch, batches):
            for game_scores in batch_results:
                for name in player_names:
                    result.scores[name].append(game_scores[name])

    return result
