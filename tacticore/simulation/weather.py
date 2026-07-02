"""Prevision del clima de un partido (cosmetico y determinista).

Por ahora es solo "sabor" para la ficha del proximo partido: el clima sale de la
fecha del encuentro + la semilla, asi siempre da lo mismo. Mas adelante el motor
de partido podria usarlo (una cancha con lluvia rinde distinto, etc.).
"""

import random

from ..domain.match import Match

_CONDITIONS = ("Soleado", "Nublado", "Lluvia", "Viento", "Frio")


def forecast(match: Match, seed: int = 0) -> str:
    """Devuelve el clima previsto para `match` (determinista por fecha + semilla)."""
    key = seed
    if match.match_date is not None:
        key += match.match_date.toordinal()
    return random.Random(key).choice(_CONDITIONS)
