"""
Ranked points scoring: 6-5-4-3-2-1 per game based on finish position.
Lower penalty score = better rank = more points.
Ties split points evenly.

Runs the full rotating 6-player mixed tournament, reports:
  - Mean ranked points per game (higher = better)
  - Point share % (higher = better)
  - Head-to-head ranked points matrix
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import statistics
from itertools import combinations
from multiprocessing import Pool, cpu_count
from game.game import Game

from strategies.random_strategy import RandomStrategy
from strategies.lowest_card import LowestCardStrategy
from strategies.highest_card import HighestCardStrategy
from strategies.greedy import GreedyStrategy
from strategies.cautious import CautiousStrategy
from strategies.midrange import MidRangeStrategy
from strategies.safe_placement import SafePlacementStrategy
from strategies.gap_hunter import GapHunterStrategy
from strategies.penalty_dodger import PenaltyDodgerStrategy
from strategies.equalizer import EqualizerStrategy
from strategies.corner_pusher import CornerPusherStrategy

REGISTRY = {
    "Random":        RandomStrategy,
    "LowestCard":    LowestCardStrategy,
    "HighestCard":   HighestCardStrategy,
    "Greedy":        GreedyStrategy,
    "Cautious":      CautiousStrategy,
    "MidRange":      MidRangeStrategy,
    "SafePlace":     SafePlacementStrategy,
    "GapHunter":     GapHunterStrategy,
    "PenaltyDodger": PenaltyDodgerStrategy,
    "Equalizer":     EqualizerStrategy,
    "CornerPusher":  CornerPusherStrategy,
}

BASE_SEED = 42
N_GAMES = 20_000
RANK_POINTS = [6, 5, 4, 3, 2, 1]   # 1st → 6 pts, 6th → 1 pt


def _rank_points(scores: dict[str, int]) -> dict[str, float]:
    """Convert penalty scores to rank points. Ties split evenly."""
    sorted_players = sorted(scores.items(), key=lambda x: x[1])
    n = len(sorted_players)
    points = {}
    i = 0
    while i < n:
        j = i
        while j < n and sorted_players[j][1] == sorted_players[i][1]:
            j += 1
        # players i..j-1 tied — average their rank points
        rank_pts = [RANK_POINTS[r] for r in range(i, j) if r < len(RANK_POINTS)]
        avg_pts = sum(rank_pts) / len(rank_pts) if rank_pts else 0.5
        for k in range(i, j):
            points[sorted_players[k][0]] = avg_pts
        i = j
    return points


def _cls_path(cls):
    return (cls.__module__, cls.__name__)


def _run_rotating_ranked(args):
    import importlib
    from game.game import Game as _G
    seeds_batch, lineups_batch, snames, cpaths = args
    def load(m, c): return getattr(importlib.import_module(m), c)
    classes = [load(*p) for p in cpaths]
    results = []
    for seed, lineup in zip(seeds_batch, lineups_batch):
        pnames = [snames[i] for i in lineup]
        strats = {n: classes[i]() for n, i in zip(pnames, lineup)}
        gr = _G(pnames, strats, seed=seed).run()
        rp = _rank_points(gr.scores)
        results.append((lineup, rp))
    return results


def run_ranked_tournament(n_games=N_GAMES):
    strat_names = list(REGISTRY.keys())
    n_strats = len(strat_names)
    cls_paths = [_cls_path(REGISTRY[n]) for n in strat_names]

    combos = list(combinations(range(n_strats), 6))
    lineups = [combos[i % len(combos)] for i in range(n_games)]
    seeds = list(range(BASE_SEED, BASE_SEED + n_games))

    n_workers = max(1, cpu_count() - 1)
    batch_size = max(1, len(seeds) // n_workers)
    batches = [
        (seeds[i:i+batch_size], lineups[i:i+batch_size], strat_names, cls_paths)
        for i in range(0, len(seeds), batch_size)
    ]

    # Accumulate ranked points per strat
    ranked_pts = {n: [] for n in strat_names}
    game_counts = {n: 0 for n in strat_names}

    with Pool(n_workers) as pool:
        for batch in pool.map(_run_rotating_ranked, batches):
            for lineup, rp in batch:
                for i in lineup:
                    n = strat_names[i]
                    ranked_pts[n].append(rp[n])
                    game_counts[n] += 1

    print("\n" + "="*70)
    print(f"  RANKED POINTS (6-5-4-3-2-1 by finish position, {n_games} games)")
    print("="*70)
    print(f"\n  {'Strategy':<16} {'Games':>6} {'Avg pts':>8} {'Pts/game%':>10} {'1st place%':>11}")
    print("  " + "-"*56)

    max_possible = max(RANK_POINTS)   # 6
    results_summary = {}
    for n in strat_names:
        pts = ranked_pts[n]
        avg = statistics.mean(pts)
        pct = avg / max_possible * 100
        first_pct = pts.count(max_possible) / len(pts) * 100
        results_summary[n] = {"avg": avg, "pct": pct, "first_pct": first_pct, "n": len(pts)}

    for n in sorted(results_summary, key=lambda x: -results_summary[x]["avg"]):
        r = results_summary[n]
        print(
            f"  {n:<16} {r['n']:>6} {r['avg']:>8.3f} {r['pct']:>9.1f}% {r['first_pct']:>10.1f}%"
        )

    best = max(results_summary, key=lambda x: results_summary[x]["avg"])
    print(f"\n  >>> BEST: {best} ({results_summary[best]['avg']:.3f} pts/game avg) <<<")

    # Head-to-head ranked points matrix (sample: pairs of 2 focal + 4 random)
    print("\n" + "="*70)
    print("  HEAD-TO-HEAD RANKED POINTS MATRIX")
    print("  (focal pair + 4 Random fillers, 3000 games/pair)")
    print("="*70)

    from strategies.random_strategy import RandomStrategy as Rnd
    h2h = {a: {b: None for b in strat_names} for a in strat_names}

    pairs = list(combinations(strat_names, 2))
    n_h2h = 3000

    def _run_h2h(args):
        import importlib
        from game.game import Game as _G
        seeds_b, a_name, b_name, a_path, b_path, rnd_path = args
        def load(m, c): return getattr(importlib.import_module(m), c)
        cls_a = load(*a_path)
        cls_b = load(*b_path)
        cls_r = load(*rnd_path)
        # Deduplicate player names
        pnames = [f"{a_name}_1", f"{a_name}_2", f"{b_name}_1", f"{b_name}_2", "R1", "R2"]
        scores_a, scores_b = [], []
        for seed in seeds_b:
            strats = {
                f"{a_name}_1": cls_a(), f"{a_name}_2": cls_a(),
                f"{b_name}_1": cls_b(), f"{b_name}_2": cls_b(),
                "R1": cls_r(), "R2": cls_r(),
            }
            gr = _G(pnames, strats, seed=seed).run()
            rp = _rank_points(gr.scores)
            scores_a.append((rp[f"{a_name}_1"] + rp[f"{a_name}_2"]) / 2)
            scores_b.append((rp[f"{b_name}_1"] + rp[f"{b_name}_2"]) / 2)
        return statistics.mean(scores_a), statistics.mean(scores_b)

    rnd_path = _cls_path(RandomStrategy)
    h2h_args = [
        (list(range(1000 + i * 10, 1000 + i * 10 + n_h2h)), a, b,
         _cls_path(REGISTRY[a]), _cls_path(REGISTRY[b]), rnd_path)
        for i, (a, b) in enumerate(pairs)
    ]

    with Pool(n_workers) as pool:
        h2h_results = pool.map(_run_h2h, h2h_args)

    for (a, b), (pa, pb) in zip(pairs, h2h_results):
        h2h[a][b] = pa
        h2h[b][a] = pb

    # Print compact matrix
    short = {n: n[:8] for n in strat_names}
    header = f"  {'':16}" + "".join(f"{short[n]:>10}" for n in strat_names)
    print(f"\n{header}")
    print("  " + "-" * (16 + 10 * len(strat_names)))
    for a in strat_names:
        row = f"  {a:<16}"
        for b in strat_names:
            if a == b:
                row += f"{'  ---':>10}"
            else:
                v = h2h[a][b]
                row += f"{v:>10.2f}"
        row_avg = statistics.mean(v for b, v in h2h[a].items() if v is not None)
        row += f"  avg={row_avg:.2f}"
        print(row)

    print()
    return results_summary, h2h


if __name__ == "__main__":
    run_ranked_tournament()
