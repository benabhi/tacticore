"""Entidad Prospect: un juvenil que un ojeador trajo a la Cantera.

Cada tanto (dos veces por temporada) los ojeadores del club descubren juveniles.
Cada hallazgo es un `Prospect`: envuelve al `Player` juvenil, guarda la calidad
del ojeador que lo trajo (`scout_skill`, define cuanto se revela y que tan bueno
es), si el manager ya reviso el informe (`revealed`) y las fechas de aparicion y
vencimiento (si no se decide, caduca). La logica (descubrir, fichar, descartar)
vive en `simulation/youth.py`.
"""

from dataclasses import dataclass
from datetime import date

from .player import Player


@dataclass
class Prospect:
    """Un juvenil descubierto por un ojeador, a la espera de decision."""

    player: Player
    scout_skill: float        # calidad del ojeador que lo trajo (1-100)
    found_date: date          # cuando lo trajo la camada
    expires: date             # hasta cuando queda disponible (si no, caduca)
    revealed: bool = False    # si el manager ya reviso el informe (descubrio los datos)
