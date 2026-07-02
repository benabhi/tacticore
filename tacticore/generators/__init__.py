"""Generacion procedural del mundo de fantasia.

Cada generador recibe un `random.Random` para ser determinista: misma semilla
-> mismo resultado. Los datos crudos (silabas, prefijos, paises) viven en
`data/`. `WorldGenerator` orquesta a los demas para armar el mundo completo.
"""

from .club_generator import ClubGenerator
from .coach_generator import CoachGenerator
from .manager_generator import ManagerGenerator
from .name_generator import NameGenerator
from .player_generator import PlayerGenerator
from .stadium_generator import StadiumGenerator
from .world_generator import WorldGenerator

__all__ = [
    "ClubGenerator",
    "CoachGenerator",
    "ManagerGenerator",
    "NameGenerator",
    "PlayerGenerator",
    "StadiumGenerator",
    "WorldGenerator",
]
