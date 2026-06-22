"""Generador de clubes de fantasia (con su plantilla)."""

import random

from ..domain.club import Club
from ..domain.enums import Position
from .name_generator import NameGenerator
from .player_generator import PlayerGenerator


class ClubGenerator:
    """Crea clubes con nombre y una plantilla generada."""

    def __init__(
        self,
        rng: random.Random | None = None,
        names: NameGenerator | None = None,
    ) -> None:
        self._rng = rng or random.Random()
        self._names = names or NameGenerator(self._rng)
        self._players = PlayerGenerator(self._rng, self._names)

    def generate(self, squad_size: int = 18) -> Club:
        """Genera un club con una plantilla de `squad_size` jugadores.

        Garantiza al menos 2 arqueros; el resto de las posiciones son al azar.
        """
        name = self._names.club_name()
        # Nombre corto: las dos palabras reducidas a sus iniciales/nucleo.
        short_name = "".join(part[:3] for part in name.split()).upper()[:5]

        players = [self._players.generate(Position.GOALKEEPER) for _ in range(2)]
        players += [self._players.generate() for _ in range(squad_size - 2)]

        # Asignar dorsales y club de origen (por ahora asumimos canteranos).
        for number, player in enumerate(players, start=1):
            player.shirt_number = number
            player.origin_club = name

        return Club(
            name=name,
            short_name=short_name,
            players=players,
            budget=self._rng.randint(1, 50) * 1_000_000,
        )
