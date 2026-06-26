"""
Mixed-table ELO tournament.

Each game has 6 seats filled by a specific composition of strategies.
Table compositions are defined explicitly — realistic scenarios of what
a real game night looks like.

ELO is updated after every game via pairwise comparisons.
Each strategy accumulates ELO across ALL tables it appears in.

Table compositions (6 seats each):
  Each entry is a list of strat names (with repetition = multiple seats).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import statistics
from itertools import combinations
from multiprocessing import Pool, cpu_count

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

# ── Table compositions ────────────────────────────────────────────────────
# Format: (label, [strat_name × 6])
TABLE_COMPOSITIONS = [
    # --- Pure tables ---
    ("pure_random",     ["Random"] * 6),
    ("pure_highest",    ["HighestCard"] * 6),
    ("pure_midrange",   ["MidRange"] * 6),
    ("pure_greedy",     ["Greedy"] * 6),
    ("pure_gaphunter",  ["GapHunter"] * 6),

    # --- 2+2+2 balanced splits ---
    ("2H+2M+2R",        ["HighestCard","HighestCard","MidRange","MidRange","Random","Random"]),
    ("2H+2G+2C",        ["HighestCard","HighestCard","Greedy","Greedy","Cautious","Cautious"]),
    ("2M+2G+2P",        ["MidRange","MidRange","Greedy","Greedy","PenaltyDodger","PenaltyDodger"]),
    ("2G+2GH+2CP",      ["Greedy","Greedy","GapHunter","GapHunter","CornerPusher","CornerPusher"]),
    ("2H+2L+2E",        ["HighestCard","HighestCard","LowestCard","LowestCard","Equalizer","Equalizer"]),
    ("2SP+2PD+2R",      ["SafePlace","SafePlace","PenaltyDodger","PenaltyDodger","Random","Random"]),

    # --- 3+2+1 asymmetric ---
    ("3H+2R+1M",        ["HighestCard","HighestCard","HighestCard","Random","Random","MidRange"]),
    ("3R+2H+1G",        ["Random","Random","Random","HighestCard","HighestCard","Greedy"]),
    ("3M+2G+1H",        ["MidRange","MidRange","MidRange","Greedy","Greedy","HighestCard"]),
    ("3G+2C+1CP",       ["Greedy","Greedy","Greedy","Cautious","Cautious","CornerPusher"]),
    ("3PD+2GH+1L",      ["PenaltyDodger","PenaltyDodger","PenaltyDodger","GapHunter","GapHunter","LowestCard"]),

    # --- Shark tank: dominant strat + 5 others ---
    ("shark_H+5M",      ["HighestCard","MidRange","MidRange","MidRange","MidRange","MidRange"]),
    ("shark_GH+5R",     ["GapHunter","Random","Random","Random","Random","Random"]),
    ("shark_M+5H",      ["MidRange","HighestCard","HighestCard","HighestCard","HighestCard","HighestCard"]),
    ("shark_CP+5G",     ["CornerPusher","Greedy","Greedy","Greedy","Greedy","Greedy"]),

    # --- Chaos: all different ---
    ("chaos_6diff_A",   ["HighestCard","MidRange","Greedy","Random","GapHunter","PenaltyDodger"]),
    ("chaos_6diff_B",   ["Cautious","SafePlace","CornerPusher","Equalizer","LowestCard","Random"]),
    ("chaos_6diff_C",   ["HighestCard","GapHunter","PenaltyDodger","CornerPusher","MidRange","Greedy"]),
    ("chaos_6diff_D",   ["SafePlace","Cautious","Equalizer","Random","LowestCard","HighestCard"]),

    # --- Beginner tables (Random-heavy) ---
    ("beginner_1smart", ["Random","Random","Random","Random","Random","HighestCard"]),
    ("beginner_2smart", ["Random","Random","Random","Random","HighestCard","MidRange"]),
    ("beginner_3smart", ["Random","Random","Random","HighestCard","MidRange","Greedy"]),

    # --- Expert tables (no Random) ---
    ("expert_6top",     ["HighestCard","MidRange","GapHunter","PenaltyDodger","SafePlace","Greedy"]),
    ("expert_alt",      ["HighestCard","MidRange","Cautious","CornerPusher","Equalizer","SafePlace"]),
    ("expert_no_H",     ["MidRange","GapHunter","PenaltyDodger","SafePlace","Greedy","CornerPusher"]),

    # --- Counter-meta: designed to beat HighestCard ---
    ("counter_H",       ["MidRange","MidRange","GapHunter","PenaltyDodger","Greedy","Cautious"]),
    ("counter_H2",      ["Equalizer","SafePlace","CornerPusher","PenaltyDodger","MidRange","Greedy"]),
]

BASE_ELO = 1500
K = 32
N_GAMES_PER_TABLE = 5000
BASE_SEED = 77777


# ── Workers ───────────────────────────────────────────────────────────────

def _cls_path(cls):
    return (cls.__module__, cls.__name__)


def _run_table_batch(args):
    import importlib
    from game.game import Game as _G
    seeds, composition, cls_map = args

    def load(m, c): return getattr(importlib.import_module(m), c)
    classes = {n: load(*p) for n, p in cls_map.items()}

    results = []
    for seed in seeds:
        # Deduplicate player names: HighestCard_0, HighestCard_1, ...
        counts = {}
        pnames = []
        for sname in composition:
            idx = counts.get(sname, 0)
            counts[sname] = idx + 1
            pnames.append(f"{sname}_{idx}")

        strat_map = {f"{sname}_{i}": sname
                     for sname in set(composition)
                     for i in range(counts[sname])}

        strats = {pn: classes[strat_map[pn]]() for pn in pnames}
        gr = _G(pnames, strats, seed=seed).run()
        results.append((strat_map, gr.scores))
    return results


# ── ELO ───────────────────────────────────────────────────────────────────

def _update_elo(elo, strat_map, game_scores, k=K):
    players = list(game_scores.keys())
    for pa, pb in combinations(players, 2):
        sa, sb = game_scores[pa], game_scores[pb]
        na, nb = strat_map[pa], strat_map[pb]
        actual_a = 1.0 if sa < sb else (0.0 if sa > sb else 0.5)
        expected_a = 1.0 / (1 + 10 ** ((elo[nb] - elo[na]) / 400))
        delta = k * (actual_a - expected_a)
        elo[na] += delta
        elo[nb] -= delta


# ── Main ──────────────────────────────────────────────────────────────────

def run(n_games: int = N_GAMES_PER_TABLE):
    strat_names = list(REGISTRY.keys())
    cls_map = {n: _cls_path(REGISTRY[n]) for n in strat_names}
    n_workers = max(1, cpu_count() - 1)

    elo = {n: float(BASE_ELO) for n in strat_names}

    # per-table mean scores: strat -> list of mean scores across tables it appeared in
    appearances = {n: [] for n in strat_names}   # strat -> list of per-game penalties
    table_results = {}                             # label -> {strat: mean_score}

    total_tables = len(TABLE_COMPOSITIONS)
    print(f"\n{'='*68}")
    print(f"  MIXED-TABLE ELO — {total_tables} table compositions × {n_games} games each")
    print(f"  {len(strat_names)} strategies, K={K}")
    print(f"{'='*68}\n")

    for t_idx, (label, composition) in enumerate(TABLE_COMPOSITIONS):
        strats_in_table = sorted(set(composition))
        seeds = list(range(BASE_SEED + t_idx * n_games, BASE_SEED + t_idx * n_games + n_games))
        batch_size = max(1, len(seeds) // n_workers)
        batches = [
            (seeds[i:i+batch_size], composition, cls_map)
            for i in range(0, len(seeds), batch_size)
        ]

        per_strat_scores = {s: [] for s in strats_in_table}

        with Pool(n_workers) as pool:
            for batch in pool.map(_run_table_batch, batches):
                for strat_map, game_scores in batch:
                    _update_elo(elo, strat_map, game_scores)
                    # Aggregate by strat (average if strat has multiple seats)
                    strat_totals = {}
                    strat_counts = {}
                    for pn, score in game_scores.items():
                        sn = strat_map[pn]
                        strat_totals[sn] = strat_totals.get(sn, 0) + score
                        strat_counts[sn] = strat_counts.get(sn, 0) + 1
                    for sn in strats_in_table:
                        avg = strat_totals[sn] / strat_counts[sn]
                        per_strat_scores[sn].append(avg)
                        appearances[sn].append(avg)

        table_means = {s: statistics.mean(v) for s, v in per_strat_scores.items()}
        table_results[label] = table_means
        winner = min(table_means, key=table_means.get)

        seats_str = ", ".join(
            f"{s}×{composition.count(s)}" if composition.count(s) > 1 else s
            for s in strats_in_table
        )
        print(f"  [{t_idx+1:02d}/{total_tables}] {label:<22}  winner: {winner:<14} "
              f"({table_means[winner]:.1f} pts)   [{seats_str}]")

    # ── Per-table breakdown per strat ─────────────────────────────────────
    print(f"\n{'='*68}")
    print("  PER-STRATEGY SUMMARY ACROSS ALL TABLES")
    print(f"{'='*68}")
    print(f"\n  {'Strategy':<16} {'Tables':>7} {'Mean':>7} {'Best table score':>18}  {'ELO':>7}")
    print("  " + "-"*60)

    summary = {}
    for n in strat_names:
        vals = appearances[n]
        if not vals:
            continue
        summary[n] = {
            "n_tables": len([l for l, comp in TABLE_COMPOSITIONS if n in comp]),
            "mean": statistics.mean(vals),
            "best": min(vals),
            "elo": elo[n],
        }

    for n in sorted(summary, key=lambda x: -summary[x]["elo"]):
        s = summary[n]
        print(f"  {n:<16} {s['n_tables']:>7} {s['mean']:>7.2f} {s['best']:>18.2f}  {s['elo']:>7.0f}")

    # ── Table heatmap: who wins which table ───────────────────────────────
    print(f"\n{'='*68}")
    print("  TABLE WINNERS (who scores lowest per table)")
    print(f"{'='*68}\n")

    win_counts = {n: 0 for n in strat_names}
    for label, means in table_results.items():
        winner = min(means, key=means.get)
        win_counts[winner] += 1
        margin = sorted(means.values())[1] - means[winner] if len(means) > 1 else 0
        print(f"  {label:<24} → {winner:<14} Δ={margin:+.1f} vs 2nd")

    print(f"\n  Table wins:")
    for n in sorted(win_counts, key=lambda x: -win_counts[x]):
        if win_counts[n] > 0:
            print(f"    {n:<16} {win_counts[n]} wins")

    # ── Final ELO ─────────────────────────────────────────────────────────
    print(f"\n{'='*68}")
    print("  FINAL ELO RANKING")
    print(f"{'='*68}\n")
    print(f"  {'Rank':<5} {'Strategy':<16} {'ELO':>8} {'Delta':>8} {'Table wins':>11}")
    print("  " + "-"*52)
    for rank, n in enumerate(sorted(strat_names, key=lambda x: -elo[x]), 1):
        delta = elo[n] - BASE_ELO
        wins = win_counts[n]
        bar = "█" * wins
        print(f"  {rank:<5} {n:<16} {elo[n]:>8.0f} {delta:>+8.0f} {wins:>6}  {bar}")

    best = max(strat_names, key=lambda x: elo[x])
    print(f"\n  >>> ELO CHAMPION: {best} ({elo[best]:.0f}, +{elo[best]-BASE_ELO:.0f}) <<<\n")
    return elo, table_results, win_counts


if __name__ == "__main__":
    run(n_games=5000)
