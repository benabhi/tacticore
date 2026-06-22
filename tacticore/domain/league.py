"""Entidad Liga.

Una liga pertenece a un pais y tiene un nivel (tier A-E). La tabla de
posiciones y el calendario de jornadas llegaran con el motor de temporada
(`simulation/season.py`).
"""

from dataclasses import dataclass, field

from .club import Club
from .enums import LeagueTier


@dataclass
class League:
    """Una liga: nombre, nivel, pais y clubes participantes."""

    name: str
    tier: LeagueTier
    country_code: str
    clubs: list[Club] = field(default_factory=list)
    # TODO: tabla de posiciones, calendario de jornadas, temporada actual.
