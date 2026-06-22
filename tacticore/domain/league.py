"""Entidad Liga y tabla de posiciones.

ESQUELETO: se completara cuando exista el motor de temporada
(`simulation/season.py`). Por ahora define la forma minima de los datos.
"""

from dataclasses import dataclass, field

from .club import Club


@dataclass
class League:
    """Una liga: nombre y clubes participantes."""

    name: str
    clubs: list[Club] = field(default_factory=list)
    # TODO: tabla de posiciones, calendario de jornadas, temporada actual.
