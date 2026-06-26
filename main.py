#!/usr/bin/env python3
"""Entry point: run a tournament and print results."""

from simulation.runner import run_tournament
from strategies.random_strategy import RandomStrategy

N_PLAYERS = 6
N_GAMES = 10_000

factories = {
    f"Random_{i+1}": RandomStrategy
    for i in range(N_PLAYERS)
}

if __name__ == "__main__":
    print(f"Running {N_GAMES} games with {N_PLAYERS} random players...")
    result = run_tournament(factories, n_games=N_GAMES)
    result.print_summary()
