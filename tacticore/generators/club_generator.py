"""Generador de clubes de fantasia (con su plantilla y estadio)."""

import random

from ..domain.club import Club
from ..domain.enums import LeagueTier, Position
from .name_generator import NameGenerator
from .player_generator import PlayerGenerator
from .stadium_generator import StadiumGenerator

# Capital inicial (en millones) y rango de asociados segun el nivel de la liga.
_TIER_CAPITAL: dict[LeagueTier, tuple[int, int]] = {
    LeagueTier.A: (20, 80),
    LeagueTier.B: (10, 40),
    LeagueTier.C: (5, 20),
    LeagueTier.D: (2, 10),
    LeagueTier.E: (1, 5),
}
_TIER_MEMBERS: dict[LeagueTier, tuple[int, int]] = {
    LeagueTier.A: (40_000, 120_000),
    LeagueTier.B: (20_000, 60_000),
    LeagueTier.C: (8_000, 30_000),
    LeagueTier.D: (3_000, 12_000),
    LeagueTier.E: (500, 5_000),
}


class ClubGenerator:
    """Crea clubes con nombre, finanzas, estadio y plantilla generada."""

    def __init__(
        self,
        rng: random.Random | None = None,
        names: NameGenerator | None = None,
    ) -> None:
        self._rng = rng or random.Random()
        self._names = names or NameGenerator(self._rng)
        self._players = PlayerGenerator(self._rng, self._names)
        self._stadiums = StadiumGenerator(self._rng)

    def generate(
        self,
        squad_size: int = 16,
        country_code: str = "FAN",
        tier: LeagueTier = LeagueTier.E,
    ) -> Club:
        """Genera un club de la liga `tier` en el pais `country_code`.

        Garantiza al menos 2 arqueros; el resto de las posiciones son al azar.
        """
        name = self._names.club_name()
        # Nombre corto: las dos palabras reducidas a sus iniciales/nucleo.
        short_name = "".join(part[:3] for part in name.split()).upper()[:5]
        stadium = self._stadiums.generate(tier, name)

        players = [
            self._players.generate(Position.GOALKEEPER, tier) for _ in range(2)
        ]
        players += [
            self._players.generate(tier=tier) for _ in range(squad_size - 2)
        ]

        # Asignar dorsales y club de origen (por ahora asumimos canteranos).
        for number, player in enumerate(players, start=1):
            player.shirt_number = number
            player.origin_club = name

        capital = self._rng.randint(*_TIER_CAPITAL[tier]) * 1_000_000
        members = self._rng.randint(*_TIER_MEMBERS[tier])

        return Club(
            name=name,
            short_name=short_name,
            country_code=country_code,
            tier=tier,
            stadium=stadium,
            capital=capital,
            members=members,
            players=players,
        )
