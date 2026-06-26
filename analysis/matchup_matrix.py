"""
Matchup matrix: for each strategy, score against every possible opponent composition.

Setup: 1 focal player + 5 opponents drawn from all strategies (with repetition allowed).
Reports: mean score of focal player per opponent context.

Also runs: full 11-way mixed tournament to rank all strategies competitively.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import statistics
from itertools import combinations_with_replacement
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

N_GAMES = 5000       # per matchup cell
N_OPPONENTS = 5      # focal + 5 = 6 players total
BASE_SEED = 42


# ── helpers picklable for multiprocessing ──────────────────────────────────

def _run_batch(args):
    import importlib
    seeds, focal_name, focal_cls_path, opp_names, opp_cls_paths = args

    def load(module, clsname):
        return getattr(importlib.import_module(module), clsname)

    focal_cls = load(*focal_cls_path)
    opp_classes = [load(*p) for p in opp_cls_paths]

    player_names = [focal_name] + opp_names
    scores = []
    for seed in seeds:
        strats = {focal_name: focal_cls()}
        for n, cls in zip(opp_names, opp_classes):
            strats[n] = cls()
        game = Game(player_names, strats, seed=seed)
        scores.append(game.run().scores[focal_name])
    return scores


def _cls_path(cls):
    return (cls.__module__, cls.__name__)


def _run_mixed_batch(args):
    import importlib
    from game.game import Game as _Game
    seeds_batch, pnames, cpaths = args
    def load(m, c): return getattr(importlib.import_module(m), c)
    classes = [load(*p) for p in cpaths]
    results = []
    for seed in seeds_batch:
        strats = {n: cls() for n, cls in zip(pnames, classes)}
        gr = _Game(pnames, strats, seed=seed).run()
        results.append(gr.scores)
    return results


def _run_rotating_batch(args):
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
        results.append((lineup, gr.scores))
    return results


# ── 1. Mixed tournament: all 11 strats, 6 players per game ───────────────
#
# With 11 strats and max 6 players/game, we rotate: each game picks 6 strats
# (one seat per strat from a round-robin cycle), ensuring every strat plays
# the same number of games and faces all others over many iterations.

def run_mixed_all(n_games=10000):
    print("\n" + "="*65)
    print("  MIXED TOURNAMENT — all 11 strategies, 6 players/game (rotating)")
    print("="*65)

    strat_names = list(REGISTRY.keys())
    n_strats = len(strat_names)
    all_scores = {n: [] for n in strat_names}

    n_workers = max(1, cpu_count() - 1)
    seeds = list(range(BASE_SEED, BASE_SEED + n_games))

    # Build rotating 6-player lineups: cycle through all combos
    from itertools import combinations
    combos = list(combinations(range(n_strats), 6))
    # repeat combos to cover n_games
    lineups = [combos[i % len(combos)] for i in range(n_games)]

    cls_paths = [_cls_path(REGISTRY[n]) for n in strat_names]

    batch_size = max(1, len(seeds) // n_workers)
    batches = [
        (seeds[i:i+batch_size], lineups[i:i+batch_size], strat_names, cls_paths)
        for i in range(0, len(seeds), batch_size)
    ]

    with Pool(n_workers) as pool:
        for batch in pool.map(_run_rotating_batch, batches):
            for lineup, gs in batch:
                for i in lineup:
                    n = strat_names[i]
                    all_scores[n].append(gs[n])

    print(f"\n  {'Strategy':<16} {'N games':>8} {'Mean':>7} {'Median':>7} {'Stdev':>6}")
    print("  " + "-"*52)
    ranking = sorted(strat_names, key=lambda n: statistics.mean(all_scores[n]))
    for n in ranking:
        s = all_scores[n]
        print(
            f"  {n:<16} {len(s):>8} {statistics.mean(s):>7.2f} "
            f"{statistics.median(s):>7.1f} {statistics.stdev(s):>6.1f}"
        )
    return all_scores


# ── 2. Matchup matrix: focal vs opponent composition ──────────────────────

def run_matchup_matrix(n_games_per_cell=N_GAMES):
    """
    For each focal strategy × each unique opponent composition (5 opponents
    chosen with replacement from all strategies), compute mean focal score.

    With 11 strats and 5 opponents: C(11+5-1,5) = 3003 combinations.
    Too many to run exhaustively — instead sample representative subsets:
      - vs 5× same (pure)
      - vs 4× same + 1× each other
      - vs full mixed (each other strat once + 1 random filler)
    """
    strat_names = list(REGISTRY.keys())
    n_workers = max(1, cpu_count() - 1)

    print("\n" + "="*65)
    print("  MATCHUP MATRIX: focal strat vs key opponent compositions")
    print("="*65)

    # Define opponent profiles to test against each focal strat
    profiles = {
        "vs 5×Same":     lambda focal: [focal] * 5,
        "vs 5×Random":   lambda focal: ["Random"] * 5,
        "vs 5×HighCard": lambda focal: ["HighestCard"] * 5,
        "vs 5×MidRange": lambda focal: ["MidRange"] * 5,
        "vs Mixed5":     lambda focal: [n for n in strat_names if n != focal][:5],
    }

    # matrix[focal][profile] = mean_score
    matrix = {n: {} for n in strat_names}

    for focal_name in strat_names:
        focal_cls = REGISTRY[focal_name]
        focal_path = _cls_path(focal_cls)

        for profile_name, make_opps in profiles.items():
            opp_names_raw = make_opps(focal_name)
            # deduplicate player names
            opp_names = [f"opp_{i}_{n}" for i, n in enumerate(opp_names_raw)]
            opp_paths = [_cls_path(REGISTRY[n]) for n in opp_names_raw]

            seeds = list(range(BASE_SEED, BASE_SEED + n_games_per_cell))
            batch_size = max(1, len(seeds) // n_workers)
            batches = [
                (seeds[i:i+batch_size], focal_name, focal_path, opp_names, opp_paths)
                for i in range(0, len(seeds), batch_size)
            ]

            with Pool(n_workers) as pool:
                flat = [s for batch in pool.map(_run_batch, batches) for s in batch]

            matrix[focal_name][profile_name] = statistics.mean(flat)

    # Print matrix
    col_w = 11
    profile_keys = list(profiles.keys())
    print(f"\n  {'Strategy':<16}", end="")
    for p in profile_keys:
        print(f" {p:>{col_w}}", end="")
    print(f" {'AVG':>{col_w}}")
    print("  " + "-" * (16 + (col_w + 1) * (len(profile_keys) + 1)))

    global_avgs = {}
    for name in sorted(strat_names, key=lambda n: statistics.mean(matrix[n].values())):
        vals = list(matrix[name].values())
        avg = statistics.mean(vals)
        global_avgs[name] = avg
        print(f"  {name:<16}", end="")
        for p in profile_keys:
            v = matrix[name][p]
            print(f" {v:>{col_w}.2f}", end="")
        print(f" {avg:>{col_w}.2f}")

    return matrix, global_avgs


# ── 3. Final composite ranking ─────────────────────────────────────────────

def composite_ranking(mixed_scores, matrix_avgs):
    strat_names = list(REGISTRY.keys())

    mixed_means = {n: statistics.mean(mixed_scores[n]) for n in strat_names}

    def norm(d):
        mn, mx = min(d.values()), max(d.values())
        if mx == mn:
            return {k: 0.5 for k in d}
        return {k: (v - mn) / (mx - mn) for k, v in d.items()}

    nm = norm(mixed_means)
    nmat = norm(matrix_avgs)
    composite = {n: (nm[n] + nmat[n]) / 2 for n in strat_names}

    print("\n" + "="*65)
    print("  FINAL RANKING (mixed + matchup matrix, lower = better)")
    print("="*65)
    print(f"\n  {'Strategy':<16} {'Mixed':>8} {'Matrix':>8} {'Composite':>10}")
    print("  " + "-"*46)
    for n in sorted(composite, key=composite.get):
        print(
            f"  {n:<16} {mixed_means[n]:>8.2f} {matrix_avgs[n]:>8.2f} {composite[n]:>10.3f}"
        )
    best = min(composite, key=composite.get)
    print(f"\n  >>> BEST: {best} (composite {composite[best]:.3f}) <<<\n")
    return composite


if __name__ == "__main__":
    mixed = run_mixed_all(n_games=10000)
    matrix, matrix_avgs = run_matchup_matrix(n_games_per_cell=3000)
    composite_ranking(mixed, matrix_avgs)
