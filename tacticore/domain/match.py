"""Entidad Partido (resultado de un encuentro).

ESQUELETO: lo llenara `simulation/match_engine.py`. Por ahora guarda solo el
marcador entre dos clubes.
"""

from dataclasses import dataclass

from .club import Club


@dataclass
class Match:
    """Resultado de un partido entre dos clubes."""

    home: Club
    away: Club
    home_goals: int = 0
    away_goals: int = 0
    played: bool = False
