"""Entidad Partido (un encuentro del fixture).

Guarda los dos clubes, la jornada en la que se juega y, una vez disputado, el
marcador. El marcador real lo pondra `simulation/match_engine.py`; por ahora los
partidos se generan sin jugar (`played=False`).
"""

from dataclasses import dataclass
from datetime import date

from .club import Club
from .enums import MatchKind
from .tactic import Tactic


@dataclass
class Match:
    """Un partido entre dos clubes (local y visitante) en una jornada."""

    home: Club
    away: Club
    matchday: int = 0                    # numero de jornada (1..2*(N-1))
    kind: MatchKind = MatchKind.LEAGUE   # tipo/competicion (liga, amistoso, copa)
    match_date: date | None = None       # fecha del encuentro (segun el calendario)
    home_goals: int = 0
    away_goals: int = 0
    played: bool = False
    tactic: Tactic | None = None         # planteo del club del jugador (si lo seteo)
