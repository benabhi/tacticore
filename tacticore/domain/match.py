"""Entidad Partido (un encuentro del fixture).

Guarda los dos clubes, la jornada en la que se juega y, una vez disputado, el
marcador. El marcador real lo pondra `simulation/match_engine.py`; por ahora los
partidos se generan sin jugar (`played=False`).
"""

from dataclasses import dataclass

from .club import Club


@dataclass
class Match:
    """Un partido entre dos clubes (local y visitante) en una jornada."""

    home: Club
    away: Club
    matchday: int = 0         # numero de jornada (1..2*(N-1))
    home_goals: int = 0
    away_goals: int = 0
    played: bool = False
