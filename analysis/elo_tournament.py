"""
ELO tournament: run many games across diverse table compositions,
update ELO after each game using pairwise comparisons.

ELO update rule (per game):
  For each pair of players (A, B) who played together:
    expected_A = 1 / (1 + 10^((elo_B - elo_A)/400))
    actual_A   = 1 if score_A < score_B, 0.5 if tie, 0 if score_A > score_B
    elo_A     += K * (actual_A - expected_A)

Table profiles tested:
  - random_mix:    6 players drawn uniformly from all strats
  - sharks:        5 HighestCard + 1 focal
  - fish:          5 Random + 1 focal
  - midrange_pond: 5 MidRange + 1 focal
  - diverse:       one of each top-6 strat
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import statistics
import random as _rnd
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

BASE_ELO = 1500
K = 32
N_PLAYERS = 6
BASE_SEED = 9999

PROFILES = {
    "random_mix":    None,          # handled specially: 6 random from pool
    "sharks":        "HighestCard",
    "fish":          "Random",
    "midrange_pond": "MidRange",
    "greedy_pond":   "Greedy",
}


def _cls_path(cls):
    return (cls.__module__, cls.__name__)


# ── top-level worker (picklable) ──────────────────────────────────────────

def _run_profile_batch(args):
    """Returns list of (player_name -> (strat_name, penalty_score))."""
    import importlib
    from game.game import Game as _G
    seeds, focal_name, focal_path, filler_name, filler_path, profile = args

    def load(m, c): return getattr(importlib.import_module(m), c)
    focal_cls = load(*focal_path)
    filler_cls = load(*filler_path)

    results = []
    for seed in seeds:
        pnames = [focal_name] + [f"{filler_name}_{i}" for i in range(N_PLAYERS - 1)]
        strat_map = {focal_name: focal_name}
        for i in range(N_PLAYERS - 1):
            strat_map[f"{filler_name}_{i}"] = filler_name
        strats = {focal_name: focal_cls()}
        for i in range(N_PLAYERS - 1):
            strats[f"{filler_name}_{i}"] = filler_cls()
        gr = _G(pnames, strats, seed=seed).run()
        # Return (player->strat, player->score)
        results.append((strat_map, gr.scores))
    return results


def _run_mixed_pool_batch(args):
    """6 players drawn from full pool — random_mix profile."""
    import importlib
    from game.game import Game as _G
    seeds, strat_names, cls_paths, rng_seed = args

    def load(m, c): return getattr(importlib.import_module(m), c)
    classes = {n: load(*p) for n, p in zip(strat_names, cls_paths)}

    rng = _rnd.Random(rng_seed)
    results = []
    for seed in seeds:
        chosen = rng.choices(strat_names, k=N_PLAYERS)
        pnames = [f"{n}_{i}" for i, n in enumerate(chosen)]
        strats = {pn: classes[cn]() for pn, cn in zip(pnames, chosen)}
        gr = _G(pnames, strats, seed=seed).run()
        # map back to strat names
        penalty_by_strat = {cn: gr.scores[pn] for pn, cn in zip(pnames, chosen)}
        results.append((chosen, penalty_by_strat, gr.scores, pnames))
    return results


# ── ELO update ────────────────────────────────────────────────────────────

def _update_elo(elo: dict, strat_map: dict[str, str], game_scores: dict[str, int], k: float = K):
    """
    Update ELO in-place.
    strat_map: player_name -> strat_name
    game_scores: player_name -> penalty (lower = better)
    """
    players = list(game_scores.keys())
    for pa, pb in combinations(players, 2):
        sa, sb = game_scores[pa], game_scores[pb]
        na, nb = strat_map[pa], strat_map[pb]
        if sa < sb:
            actual_a = 1.0
        elif sa > sb:
            actual_a = 0.0
        else:
            actual_a = 0.5
        expected_a = 1.0 / (1 + 10 ** ((elo[nb] - elo[na]) / 400))
        delta = k * (actual_a - expected_a)
        elo[na] += delta
        elo[nb] -= delta


# ── Main ──────────────────────────────────────────────────────────────────

def run_elo_tournament(n_games_per_profile: int = 5000):
    strat_names = list(REGISTRY.keys())
    cls_paths = [_cls_path(REGISTRY[n]) for n in strat_names]
    n_workers = max(1, cpu_count() - 1)

    elo = {n: float(BASE_ELO) for n in strat_names}
    profile_scores = {n: {p: [] for p in PROFILES} for n in strat_names}

    print(f"\n{'='*65}")
    print(f"  ELO TOURNAMENT — {n_games_per_profile} games × {len(PROFILES)} profiles")
    print(f"  {len(strat_names)} strategies, K={K}, base ELO={BASE_ELO}")
    print(f"{'='*65}")

    # ── Profile: focal vs fillers ─────────────────────────────────────────
    for profile, filler_strat in PROFILES.items():
        if profile == "random_mix":
            continue  # handled below

        filler_cls = REGISTRY[filler_strat]
        filler_path = _cls_path(filler_cls)
        seeds = list(range(BASE_SEED, BASE_SEED + n_games_per_profile))
        batch_size = max(1, len(seeds) // n_workers)

        print(f"\n  Profile: {profile} ({n_games_per_profile} games each focal vs 5×{filler_strat})")

        for focal_name in strat_names:
            focal_path = _cls_path(REGISTRY[focal_name])
            batches = [
                (seeds[i:i+batch_size], focal_name, focal_path,
                 filler_strat, filler_path, profile)
                for i in range(0, len(seeds), batch_size)
            ]
            with Pool(n_workers) as pool:
                all_results = [r for batch in pool.map(_run_profile_batch, batches) for r in batch]

            focal_pts = [scores[focal_name] for _, scores in all_results]
            profile_scores[focal_name][profile] = focal_pts

            for strat_map, game_scores in all_results:
                _update_elo(elo, strat_map, game_scores)

        # Print interim profile ranking
        ranked = sorted(strat_names, key=lambda n: statistics.mean(profile_scores[n][profile]))
        print(f"  {'Strategy':<16} {'Mean score':>12} {'ELO':>8}")
        for n in ranked:
            s = profile_scores[n][profile]
            print(f"  {n:<16} {statistics.mean(s):>12.2f} {elo[n]:>8.0f}")

    # ── Profile: random_mix ───────────────────────────────────────────────
    print(f"\n  Profile: random_mix ({n_games_per_profile} games, 6 random from pool)")
    seeds = list(range(BASE_SEED + 50000, BASE_SEED + 50000 + n_games_per_profile))
    batch_size = max(1, len(seeds) // n_workers)
    batches = [
        (seeds[i:i+batch_size], strat_names, cls_paths, BASE_SEED + i)
        for i in range(0, len(seeds), batch_size)
    ]

    mix_scores = {n: [] for n in strat_names}
    with Pool(n_workers) as pool:
        for batch in pool.map(_run_mixed_pool_batch, batches):
            for chosen, pen_by_strat, raw_scores, pnames in batch:
                strat_map = {pn: cn for pn, cn in zip(pnames, chosen)}
                _update_elo(elo, strat_map, raw_scores)
                for cn, pen in pen_by_strat.items():
                    mix_scores[cn].append(pen)
                for n in strat_names:
                    profile_scores[n]["random_mix"].extend(
                        [raw_scores[pn] for pn, cn in zip(pnames, chosen) if cn == n]
                    )

    ranked = sorted(strat_names, key=lambda n: statistics.mean(mix_scores[n]) if mix_scores[n] else 999)
    print(f"  {'Strategy':<16} {'Mean score':>12} {'ELO':>8}")
    for n in ranked:
        s = mix_scores[n]
        print(f"  {n:<16} {statistics.mean(s) if s else 0:>12.2f} {elo[n]:>8.0f}")

    # ── Final ELO ranking ─────────────────────────────────────────────────
    print(f"\n{'='*65}")
    print("  FINAL ELO RANKING")
    print(f"{'='*65}")
    print(f"\n  {'Rank':<5} {'Strategy':<16} {'ELO':>8} {'Delta':>8}")
    print("  " + "-"*42)
    for rank, name in enumerate(sorted(strat_names, key=lambda n: -elo[n]), 1):
        delta = elo[name] - BASE_ELO
        print(f"  {rank:<5} {name:<16} {elo[name]:>8.0f} {delta:>+8.0f}")

    best = max(strat_names, key=lambda n: elo[n])
    print(f"\n  >>> ELO CHAMPION: {best} ({elo[best]:.0f}) <<<\n")
    return elo


if __name__ == "__main__":
    run_elo_tournament(n_games_per_profile=8000)
