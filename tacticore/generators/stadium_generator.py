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

# Reparto de la capacidad total en sectores. Los palcos solo existen desde tier C
# (los clubes chicos no tienen); su cuota se pasa a la general en D/E.
_SECTOR_RATIOS_BIG = (0.66, 0.25, 0.08, 0.01)    # general, preferente, tribuna, palco
_SECTOR_RATIOS_SMALL = (0.67, 0.25, 0.08, 0.00)


def split_capacity(total: int, tier: LeagueTier) -> tuple[int, int, int, int]:
    """Reparte una capacidad total en (general, preferente, tribuna, palco)."""
    ratios = _SECTOR_RATIOS_BIG if tier in (LeagueTier.A, LeagueTier.B, LeagueTier.C) \
        else _SECTOR_RATIOS_SMALL
    general, preferente, tribuna, palco = (round(total * r) for r in ratios)
    # Ajuste de redondeo: que los cuatro sumen EXACTO el total (va a la general).
    general += total - (general + preferente + tribuna + palco)
    return general, preferente, tribuna, palco


class StadiumGenerator:
    """Crea estadios con capacidad (por sectores) acorde al nivel del club."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()

    def capacity_range(self, tier: LeagueTier) -> tuple[int, int]:
        """Rango (min, max) de capacidad para un club de la liga `tier`."""
        return _TIER_CAPACITY[tier]

    def generate(self, tier: LeagueTier, club_name: str) -> Stadium:
        """Genera un estadio (por sectores) para un club de la liga `tier`."""
        low, high = _TIER_CAPACITY[tier]
        capacity = self._rng.randint(low, high)
        general, preferente, tribuna, palco = split_capacity(capacity, tier)
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
        return Stadium(name=name, general=general, preferente=preferente,
                       tribuna=tribuna, palco=palco)
