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


def _strength(club: Club) -> float:
    """Fuerza del equipo: promedio de overall de sus 11 mejores (o de los que haya)."""
    if not club.players:
        return 40.0
    top = sorted(club.players, key=lambda p: p.overall, reverse=True)[:11]
    return sum(p.overall for p in top) / len(top)


def _poisson(rng: random.Random, lam: float) -> int:
    """Muestra un entero de una Poisson(lam) con el rng dado (algoritmo de Knuth)."""
    limit = math.exp(-lam)
    k, p = 0, 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= limit:
            return k - 1


def simulate_match(home: Club, away: Club, rng: random.Random) -> Match:
    """Simula un partido y devuelve un `Match` ya jugado con su marcador."""
    diff = (_strength(home) + _HOME_ADVANTAGE - _strength(away)) / 10.0
    lam_home = min(5.0, max(0.2, _BASE_GOALS + diff * _GOAL_SWING))
    lam_away = min(5.0, max(0.2, _BASE_GOALS - diff * _GOAL_SWING))
    return Match(
        home=home,
        away=away,
        home_goals=_poisson(rng, lam_home),
        away_goals=_poisson(rng, lam_away),
        played=True,
    )
