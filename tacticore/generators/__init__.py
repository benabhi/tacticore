"""Generacion procedural del mundo de fantasia (nombres, jugadores, clubes).

Cada generador recibe un `random.Random` para ser determinista: misma semilla
-> mismo resultado. Los datos crudos (silabas, prefijos) viven en `data/`.
"""

from .club_generator import ClubGenerator
from .name_generator import NameGenerator
from .player_generator import PlayerGenerator

__all__ = ["ClubGenerator", "NameGenerator", "PlayerGenerator"]
