# 6 qui prend — Simulateur de stratégies / Strategy Simulator

<p align="center">
  <img src="assets/cover.webp" alt="6 qui prend" width="220"/>
</p>

<p align="center">
  <a href="#français">🇫🇷 Français</a> &nbsp;|&nbsp; <a href="#english">🇬🇧 English</a>
</p>

---

## Français

**Objectif : trouver la meilleure stratégie possible au jeu 6 qui prend.**

Ce projet simule des centaines de milliers de parties pour comparer 17 stratégies différentes — des plus naïves (jouer au hasard) aux plus élaborées (adaptation au méta de la table, minimisation du regret, tracking des cartes adverses). Le résultat : un classement ELO sur 51 compositions de tables différentes pour savoir quelle stratégie jouer selon la situation.

### Ce que fait le projet

- Moteur de jeu complet (104 cartes, 4 rangées, jeu simultané, règles de pénalités exactes)
- 17 stratégies pluggables, du hasard pur aux agents adaptatifs avec contexte de partie
- Simulation parallèle via `multiprocessing` (~20× plus rapide)
- Système ELO sur 51 compositions de tables (255 000+ parties simulées)

### Résultats

**Champion ELO : `AdaptiveMeta` (1699)** — détecte si la table joue agressif ou défensif, et bascule dynamiquement entre style HighestCard et MidRange.

| Rang | Stratégie | ELO | Δ | Victoires de table |
|------|-----------|-----|---|--------------------|
| 1 | AdaptiveMeta | 1699 | +199 | 7 |
| 2 | RegretMin | 1686 | +186 | 2 |
| 3 | MidRange | 1611 | +111 | 6 |
| 4 | HighestCard | 1591 | +91 | **17** |
| 5 | EndgameAware | 1590 | +90 | 1 |
| 6 | SafePlace | 1585 | +85 | 0 |
| 7 | PenaltyDodger | 1561 | +61 | 3 |
| 8 | GapHunter | 1518 | +18 | 2 |
| 9 | CardTracker | 1499 | −1 | 4 |
| 10 | CornerPusher | 1490 | −10 | 3 |
| … | … | | | |
| 17 | Equalizer | 1298 | −202 | 0 |

**Guide pratique — quelle strat jouer ?**

| Situation | Meilleure stratégie |
|-----------|---------------------|
| Adversaires inconnus | **AdaptiveMeta** |
| Éviter les catastrophes | **RegretMin** |
| Pas de joueur HighestCard à table | **MidRange** |
| Table avec débutants / joueurs aléatoires | **HighestCard** |
| Table dominée par des joueurs Greedy | **CornerPusher** |

### Les 17 stratégies

#### Baselines
| Stratégie | Logique |
|-----------|---------|
| `Random` | Carte aléatoire à chaque tour |
| `LowestCard` | Toujours jouer la carte la plus basse |
| `HighestCard` | Toujours jouer la plus haute — évite les rangées pleines, atterrit sur les fraîches |
| `MidRange` | Joue la carte la plus proche du median des têtes de rangées |

#### Heuristiques
| Stratégie | Logique |
|-----------|---------|
| `Greedy` | Minimise la pénalité immédiate attendue (évite les rangées à 5 cartes) |
| `Cautious` | Comme Greedy mais pénalise massivement les rangées à 5 cartes (trop prudent) |
| `SafePlace` | Cible la rangée avec le moins de cartes (distance max avant déclenchement) |
| `GapHunter` | Cherche les grands gaps — les adversaires remplissent les slots avant vous |
| `PenaltyDodger` | Minimise P(déclenchement) × pénalité — évite les collections coûteuses |
| `Equalizer` | Maintient toutes les rangées à longueur similaire pour un board équilibré |
| `CornerPusher` | Externalise les déclenchements : joue haut pour forcer les adversaires sur les rangées dangereuses |

#### Stratégies contextuelles (utilisent `GameContext`)
| Stratégie | Logique |
|-----------|---------|
| `CompositeScorer` | Combinaison pondérée de 4 dimensions de risque |
| `EndgameAware` | Joue bas en début (beaucoup de cartes circulent), haut en fin (rangées ne se rempliront plus) |
| `ThreatAssessor` | Modélise les rangées comme des bombes : P(explosion en N tours) × pénalité |
| `CardTracker` | Suit les cartes jouées pour inférer les cartes adverses restantes |
| `AdaptiveMeta` | Détecte l'agressivité de la table ; interpole HighestCard ↔ MidRange |
| `RegretMin` | Minimax regret : minimise le pire cas, tiebreak sur la prévisibilité |

### Structure du projet

```
sixquiprend/
├── game/
│   ├── card.py            # Cartes + règles de pénalités (têtes de bœuf)
│   ├── deck.py            # Jeu de 104 cartes mélangées (seed déterministe)
│   ├── board.py           # 4 rangées, logique de placement, snapshot
│   └── game.py            # Boucle de jeu complète, construction du GameContext
├── strategies/
│   ├── base.py            # ABC Strategy + dataclass GameContext
│   └── *.py               # 17 implémentations de stratégies
├── simulation/
│   └── runner.py          # Runner de tournoi parallèle (multiprocessing)
├── analysis/
│   ├── compare.py         # Comparaison pure / mixte / H2H
│   ├── ranked_points.py   # Scoring par classement 6-5-4-3-2-1
│   ├── matchup_matrix.py  # Strat focale vs profils d'adversaires définis
│   └── mixed_table_elo.py # ELO sur 51 compositions de tables
└── main.py                # Point d'entrée rapide
```

### Utilisation

```bash
# Tournoi rapide (6 joueurs aléatoires, 10k parties)
python main.py

# Analyse ELO complète sur 51 compositions de tables
python analysis/mixed_table_elo.py

# Matrice de matchups (strat focale vs profils)
python analysis/matchup_matrix.py
```

### Ajouter une stratégie

```python
# strategies/ma_strategie.py
from strategies.base import Strategy, GameContext
from game.card import Card

class MaStrategie(Strategy):
    def choose_card(self, hand: list[Card], board: list[tuple[int,int,int]], ctx: GameContext | None = None) -> Card:
        # board = [(head_value, row_penalty, row_length), ...]
        # ctx.round_number, ctx.cards_seen_all_rounds, ctx.rounds_remaining, ...
        ...

    def choose_row(self, hand, board, card, ctx=None) -> int:
        # appelé quand card < toutes les têtes (prise forcée)
        ...
```

Puis l'ajouter au `REGISTRY` dans n'importe quel script d'analyse.

### Prérequis

Python 3.12+, aucune dépendance externe.

---

## English

**Goal: find the best possible strategy for the card game 6 qui prend (Take 6 / Category 5).**

This project simulates hundreds of thousands of games to compare 17 different strategies — from the most naive (play at random) to the most sophisticated (table meta-adaptation, regret minimization, opponent card tracking). The result: an ELO ranking across 51 table compositions to tell you which strategy to play depending on the situation.

### What it does

- Full game engine (104 cards, 4 rows, simultaneous play, correct penalty rules)
- 17 pluggable strategies, from trivial baselines to context-aware adaptive agents
- Parallel simulation via `multiprocessing` (~20× speedup)
- ELO rating system across 51 hand-crafted table compositions (255k+ games)

### Results

**ELO champion: `AdaptiveMeta` (1699)** — detects table aggressiveness from board fill rate and interpolates between HighestCard and MidRange styles dynamically.

| Rank | Strategy | ELO | Δ | Table wins |
|------|----------|-----|---|------------|
| 1 | AdaptiveMeta | 1699 | +199 | 7 |
| 2 | RegretMin | 1686 | +186 | 2 |
| 3 | MidRange | 1611 | +111 | 6 |
| 4 | HighestCard | 1591 | +91 | **17** |
| 5 | EndgameAware | 1590 | +90 | 1 |
| 6 | SafePlace | 1585 | +85 | 0 |
| 7 | PenaltyDodger | 1561 | +61 | 3 |
| 8 | GapHunter | 1518 | +18 | 2 |
| 9 | CardTracker | 1499 | −1 | 4 |
| 10 | CornerPusher | 1490 | −10 | 3 |
| … | … | | | |
| 17 | Equalizer | 1298 | −202 | 0 |

**Practical guide — which strategy to play?**

| Situation | Best strategy |
|-----------|--------------|
| Unknown opponents | **AdaptiveMeta** |
| Want to avoid catastrophes | **RegretMin** |
| No HighestCard player at table | **MidRange** |
| Beginners / Random players at table | **HighestCard** |
| Greedy-heavy table | **CornerPusher** |

### The 17 strategies

#### Baselines
| Strategy | Logic |
|----------|-------|
| `Random` | Random card each turn |
| `LowestCard` | Always play lowest card |
| `HighestCard` | Always play highest card — bypasses full rows, lands on fresh ones |
| `MidRange` | Play card closest to median of row heads |

#### Heuristic
| Strategy | Logic |
|----------|-------|
| `Greedy` | Minimize immediate expected penalty (avoid rows with 5 cards) |
| `Cautious` | Like Greedy but hard-penalizes any row with 5 cards (over-cautious) |
| `SafePlace` | Target the row with fewest cards (maximize distance from row limit) |
| `GapHunter` | Seek wide gaps above short rows — opponents fill the gap before you |
| `PenaltyDodger` | Minimize P(trigger) × row_penalty — avoid expensive collections |
| `Equalizer` | Keep all rows at similar length for a "stable" board |
| `CornerPusher` | Externalize triggers: play safe cards high to force opponents onto dangerous rows |

#### Context-aware (use `GameContext`)
| Strategy | Logic |
|----------|-------|
| `CompositeScorer` | Weighted blend of 4 risk dimensions (trigger risk, density, penalty, card value) |
| `EndgameAware` | Play low early (many opponent cards in play), high late (rows won't fill anymore) |
| `ThreatAssessor` | Model rows as ticking bombs: P(explosion in N rounds) × penalty |
| `CardTracker` | Track seen cards to infer remaining opponent cards; exploit gap coverage |
| `AdaptiveMeta` | Detect table aggressiveness from fill rate; interpolate HighestCard ↔ MidRange |
| `RegretMin` | Minimax regret: minimize worst-case outcome, tiebreak on predictability |

### Project structure

```
sixquiprend/
├── game/
│   ├── card.py            # Card + penalty rules (bulls head values)
│   ├── deck.py            # 104-card deck, shuffled with seed
│   ├── board.py           # 4 rows, placement logic, snapshot
│   └── game.py            # Full game loop, builds GameContext per turn
├── strategies/
│   ├── base.py            # Strategy ABC + GameContext dataclass
│   └── *.py               # 17 strategy implementations
├── simulation/
│   └── runner.py          # Parallel tournament runner (multiprocessing)
├── analysis/
│   ├── compare.py         # Pure / mixed / H2H comparison
│   ├── ranked_points.py   # 6-5-4-3-2-1 ranking points scoring
│   ├── matchup_matrix.py  # Focal strat vs defined opponent profiles
│   └── mixed_table_elo.py # ELO across 51 table compositions
└── main.py                # Quick entry point
```

### Usage

```bash
# Quick tournament (6 random players, 10k games)
python main.py

# Full ELO analysis across 51 table compositions
python analysis/mixed_table_elo.py

# Matchup matrix (focal strat vs defined profiles)
python analysis/matchup_matrix.py
```

### Add a strategy

```python
# strategies/my_strategy.py
from strategies.base import Strategy, GameContext
from game.card import Card

class MyStrategy(Strategy):
    def choose_card(self, hand: list[Card], board: list[tuple[int,int,int]], ctx: GameContext | None = None) -> Card:
        # board = [(head_value, row_penalty, row_length), ...]
        # ctx.round_number, ctx.cards_seen_all_rounds, ctx.rounds_remaining, ...
        ...

    def choose_row(self, hand, board, card, ctx=None) -> int:
        # called when card < all row heads (forced take)
        ...
```

Then add it to `REGISTRY` in any analysis script.

### Requirements

Python 3.12+, no dependencies beyond stdlib.
