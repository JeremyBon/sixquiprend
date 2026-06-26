"""
Strategy comparison: head-to-head and combo tournaments.

Runs two types of analysis:
1. Pure: all 6 players use the same strategy → absolute score baseline.
2. Mixed: all strategies play together in one 6-player game → competitive ranking.
3. Round-robin pairs: each pair of strategies plays 1v1 (4 fillers = Random).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import statistics
from itertools import combinations
from simulation.runner import run_tournament, TournamentResult

from strategies.random_strategy import RandomStrategy
from strategies.lowest_card import LowestCardStrategy
from strategies.highest_card import HighestCardStrategy
from strategies.greedy import GreedyStrategy
from strategies.cautious import CautiousStrategy
from strategies.midrange import MidRangeStrategy
from strategies.safe_placement import SafePlacementStrategy

N_GAMES = 20_000
N_PLAYERS = 6

REGISTRY = {
    "Random":         RandomStrategy,
    "LowestCard":     LowestCardStrategy,
    "HighestCard":    HighestCardStrategy,
    "Greedy":         GreedyStrategy,
    "Cautious":       CautiousStrategy,
    "MidRange":       MidRangeStrategy,
    "SafePlacement":  SafePlacementStrategy,
}


def _mean_score(result: TournamentResult, name: str) -> float:
    scores = [v for k, v in result.scores.items() if k.startswith(name)]
    all_vals = [s for sub in scores for s in sub]
    return statistics.mean(all_vals)


def run_pure():
    """Each strategy plays against clones of itself."""
    print("\n" + "="*60)
    print("  PURE: 6 identical players per strategy")
    print("="*60)
    results = {}
    for name, cls in REGISTRY.items():
        factories = {f"{name}_{i}": cls for i in range(N_PLAYERS)}
        r = run_tournament(factories, n_games=N_GAMES)
        mean = _mean_score(r, name)
        results[name] = mean
        print(f"  {name:<16} avg score = {mean:.2f}")

    best = min(results, key=results.get)
    print(f"\n  Best pure: {best} ({results[best]:.2f} pts/game)")
    return results


def run_mixed():
    """All 7 strategies in one game (one player each, padded with Random if <6)."""
    print("\n" + "="*60)
    print("  MIXED: all strategies play together")
    print("="*60)
    names = list(REGISTRY.keys())
    # 7 strats → one extra Random to fill 6
    factories = {name: cls for name, cls in REGISTRY.items()}
    # Pad to N_PLAYERS if needed
    while len(factories) < N_PLAYERS:
        factories[f"Random_extra_{len(factories)}"] = RandomStrategy
    # If more than N_PLAYERS, trim (all fit here: 7 strats, keep all 7)
    # Run with 7 players
    from game.game import Game, GameResult
    player_names = list(factories.keys())
    all_scores = {n: [] for n in player_names}

    for i in range(N_GAMES):
        seed = 42 + i
        strats = {name: cls() for name, cls in factories.items()}
        g = Game(player_names, strats, seed=seed)
        gr = g.run()
        for n in player_names:
            all_scores[n].append(gr.scores[n])

    print(f"\n  {'Strategy':<18} {'Mean':>7} {'Median':>7} {'Wins':>6}")
    print("  " + "-"*42)
    n_total = N_GAMES
    ranking = sorted(player_names, key=lambda n: statistics.mean(all_scores[n]))
    for n in ranking:
        s = all_scores[n]
        wins = sum(
            1 for i in range(n_total)
            if all_scores[n][i] == min(all_scores[nn][i] for nn in player_names)
        )
        print(f"  {n:<18} {statistics.mean(s):>7.2f} {statistics.median(s):>7.1f} {wins:>6}")

    return all_scores


def run_round_robin():
    """
    Each pair of strategies: 2 seats for the pair, 4 Random fillers.
    Measures head-to-head advantage in a realistic multi-player context.
    """
    print("\n" + "="*60)
    print("  ROUND-ROBIN (2v2v2: pair vs pair vs Random fillers)")
    print("="*60)

    strat_names = list(REGISTRY.keys())
    win_matrix = {a: {b: 0 for b in strat_names} for a in strat_names}
    score_matrix = {a: {b: [] for b in strat_names} for a in strat_names}

    from game.game import Game

    pairs = list(combinations(strat_names, 2))
    n_games_pair = 5000

    for a, b in pairs:
        factories = {
            f"{a}_1": REGISTRY[a],
            f"{a}_2": REGISTRY[a],
            f"{b}_1": REGISTRY[b],
            f"{b}_2": REGISTRY[b],
            "Random_5": RandomStrategy,
            "Random_6": RandomStrategy,
        }
        player_names = list(factories.keys())
        scores = {n: [] for n in player_names}

        for i in range(n_games_pair):
            strats = {n: cls() for n, cls in factories.items()}
            g = Game(player_names, strats, seed=100 + i)
            gr = g.run()
            for n in player_names:
                scores[n].append(gr.scores[n])

        mean_a = statistics.mean(scores[f"{a}_1"] + scores[f"{a}_2"])
        mean_b = statistics.mean(scores[f"{b}_1"] + scores[f"{b}_2"])

        score_matrix[a][b] = mean_a
        score_matrix[b][a] = mean_b

        winner = a if mean_a < mean_b else b
        win_matrix[winner][a if winner == b else b] += 1

        diff = mean_b - mean_a
        print(f"  {a:<16} vs {b:<16} → Δ={diff:+.2f}  ({'▲'+a if diff>0 else '▲'+b})")

    # Aggregate: mean score across all matchups
    print(f"\n  {'Strategy':<16} {'Avg H2H score':>14} {'H2H wins':>9}")
    print("  " + "-"*42)
    global_mean = {}
    for name in strat_names:
        vals = [v for k, v in score_matrix[name].items() if v]
        global_mean[name] = statistics.mean(vals) if vals else 0

    for name in sorted(strat_names, key=lambda n: global_mean[n]):
        wins = sum(win_matrix[name].values())
        print(f"  {name:<16} {global_mean[name]:>14.2f} {wins:>9}")

    return global_mean


if __name__ == "__main__":
    pure = run_pure()
    mixed = run_mixed()
    h2h = run_round_robin()

    print("\n" + "="*60)
    print("  FINAL RANKING (composite: pure + mixed + H2H)")
    print("  Lower = better (penalty points)")
    print("="*60)

    # Normalise each dimension 0-1 and average (lower=better → ascending rank)
    def normalise(d: dict) -> dict:
        mn, mx = min(d.values()), max(d.values())
        if mx == mn:
            return {k: 0.5 for k in d}
        return {k: (v - mn) / (mx - mn) for k, v in d.items()}

    strat_names = list(REGISTRY.keys())
    mixed_means = {n: statistics.mean(mixed[n]) for n in strat_names if n in mixed}

    np = normalise(pure)
    nm = normalise(mixed_means)
    nh = normalise(h2h)

    composite = {
        n: (np.get(n, 1) + nm.get(n, 1) + nh.get(n, 1)) / 3
        for n in strat_names
    }

    print(f"\n  {'Strategy':<16} {'Pure':>7} {'Mixed':>7} {'H2H':>7} {'Score':>7}")
    print("  " + "-"*50)
    for n in sorted(composite, key=composite.get):
        print(
            f"  {n:<16} {pure.get(n, 0):>7.2f} "
            f"{mixed_means.get(n, 0):>7.2f} "
            f"{h2h.get(n, 0):>7.2f} "
            f"{composite[n]:>7.3f}"
        )

    best = min(composite, key=composite.get)
    print(f"\n  >>> BEST STRATEGY: {best} (composite score {composite[best]:.3f}) <<<\n")
