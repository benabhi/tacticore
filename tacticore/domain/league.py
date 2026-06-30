"""Entidad Liga.

Una liga pertenece a un pais y tiene un nivel (tier A-E). El fixture de la
temporada (`matches`, todos contra todos ida y vuelta) lo arma
`simulation/season.py`; la tabla de posiciones se deriva de los partidos jugados.
"""

from dataclasses import dataclass, field

from .club import Club
from .enums import LeagueTier
from .match import Match


@dataclass
class League:
    """Una liga: nombre, nivel, pais, clubes y el fixture de la temporada."""

    name: str
    tier: LeagueTier
    country_code: str
    clubs: list[Club] = field(default_factory=list)
    matches: list[Match] = field(default_factory=list)  # fixture de la temporada
