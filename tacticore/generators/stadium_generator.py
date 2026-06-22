"""Generador de estadios de fantasia."""

import random

from ..domain.enums import LeagueTier
from ..domain.stadium import Stadium

# Capacidad (min, max) segun el nivel de la liga: mejor liga, estadio mas grande.
_TIER_CAPACITY: dict[LeagueTier, tuple[int, int]] = {
    LeagueTier.A: (40_000, 80_000),
    LeagueTier.B: (25_000, 50_000),
    LeagueTier.C: (12_000, 30_000),
    LeagueTier.D: (5_000, 15_000),
    LeagueTier.E: (2_000, 8_000),
}


class StadiumGenerator:
    """Crea estadios con capacidad acorde al nivel del club."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()

    def generate(self, tier: LeagueTier, club_name: str) -> Stadium:
        """Genera un estadio para un club de la liga `tier`."""
        low, high = _TIER_CAPACITY[tier]
        capacity = self._rng.randint(low, high)
        # Nombre simple a partir del nucleo del nombre del club.
        core = club_name.split()[-1]
        return Stadium(name=f"Estadio {core}", capacity=capacity)
