"""Generador de estadios de fantasia."""

import random

from ..domain.enums import LeagueTier
from ..domain.stadium import Stadium
from .name_generator import club_core

# Capacidad (min, max) segun el nivel de la liga: mejor liga, estadio mas grande.
_TIER_CAPACITY: dict[LeagueTier, tuple[int, int]] = {
    LeagueTier.A: (40_000, 80_000),
    LeagueTier.B: (25_000, 50_000),
    LeagueTier.C: (12_000, 30_000),
    LeagueTier.D: (5_000, 15_000),
    LeagueTier.E: (2_000, 8_000),
}

# Apodos genericos de estadio (raros), con su articulo ya puesto.
_STADIUM_NICKS = [
    "El Coloso", "El Templo", "El Castillo", "La Fortaleza", "La Caldera",
    "El Bastion", "El Gigante", "El Coliseo", "La Catedral", "El Fortin",
]


class StadiumGenerator:
    """Crea estadios con capacidad acorde al nivel del club."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()

    def capacity_range(self, tier: LeagueTier) -> tuple[int, int]:
        """Rango (min, max) de capacidad para un club de la liga `tier`."""
        return _TIER_CAPACITY[tier]

    def generate(self, tier: LeagueTier, club_name: str) -> Stadium:
        """Genera un estadio para un club de la liga `tier`."""
        low, high = _TIER_CAPACITY[tier]
        capacity = self._rng.randint(low, high)
        # El nombre se arma sobre el toponimo del club (no sobre un descriptor),
        # con varios formatos para dar variedad; rara vez un apodo generico.
        core = club_core(club_name)
        roll = self._rng.random()
        if roll < 0.45:
            name = f"Estadio {core}"
        elif roll < 0.60:
            name = f"Arena {core}"
        elif roll < 0.72:
            name = f"Coliseo {core}"
        elif roll < 0.82:
            name = f"Estadio Nuevo {core}"
        elif roll < 0.90:
            name = f"Estadio Monumental {core}"
        elif roll < 0.96:
            name = f"Parque {core}"
        else:
            name = self._rng.choice(_STADIUM_NICKS)
        return Stadium(name=name, capacity=capacity)
