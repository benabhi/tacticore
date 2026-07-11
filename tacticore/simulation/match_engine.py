"""Motor ESTADISTICO de un partido (resolucion rapida).

Devuelve un marcador a partir de la fuerza de las plantillas, para resolver miles
de partidos por jornada en el loop diario (ligas rivales). Es distinto del motor en
TIEMPO REAL de `simulation/match/` (ese mueve jugadores en la cancha). No imprime ni
toca la UI; es determinista con el `random.Random` que recibe.
"""

import math
import random

from ..domain.club import Club
from ..domain.match import Match

_HOME_ADVANTAGE = 4.0   # bonus de fuerza por jugar de local (en puntos de overall)
_BASE_GOALS = 1.35      # goles esperados de un equipo parejo
_GOAL_SWING = 0.35      # cuanto inclina el marcador cada 10 puntos de diferencia
# Efecto de la familiaridad con la formacion: cada punto de familiaridad por encima
# (o debajo) de 50 suma (o resta) esto a la fuerza. Familiaridad 100 -> ~+4 overall.
_FAM_WEIGHT = 0.08


def _strength(club: Club, familiarity: float = 50.0) -> float:
    """Fuerza del equipo: promedio de overall de sus 11 mejores, ajustada por cuan
    entrenada esta la formacion que juega (familiaridad 1-100; 50 = neutro)."""
    if not club.players:
        base = 40.0
    else:
        top = sorted(club.players, key=lambda p: p.overall, reverse=True)[:11]
        base = sum(p.overall for p in top) / len(top)
    return base + (familiarity - 50.0) * _FAM_WEIGHT


def _poisson(rng: random.Random, lam: float) -> int:
    """Muestra un entero de una Poisson(lam) con el rng dado (algoritmo de Knuth)."""
    limit = math.exp(-lam)
    k, p = 0, 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= limit:
            return k - 1


def simulate_match(home: Club, away: Club, rng: random.Random,
                   home_fam: float = 50.0, away_fam: float = 50.0) -> Match:
    """Simula un partido y devuelve un `Match` ya jugado con su marcador.

    `home_fam`/`away_fam` (1-100, 50 = neutro) son la familiaridad de cada equipo con
    la formacion que juega: una formacion poco entrenada rinde peor."""
    diff = (_strength(home, home_fam) + _HOME_ADVANTAGE - _strength(away, away_fam)) / 10.0
    lam_home = min(5.0, max(0.2, _BASE_GOALS + diff * _GOAL_SWING))
    lam_away = min(5.0, max(0.2, _BASE_GOALS - diff * _GOAL_SWING))
    return Match(
        home=home,
        away=away,
        home_goals=_poisson(rng, lam_home),
        away_goals=_poisson(rng, lam_away),
        played=True,
    )
