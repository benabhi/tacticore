"""Generador de jugadores de fantasia."""

import random

from ..domain.enums import Foot, Position
from ..domain.player import Player
from .name_generator import NameGenerator


class PlayerGenerator:
    """Crea jugadores con nombre y atributos aleatorios (deterministas)."""

    def __init__(
        self,
        rng: random.Random | None = None,
        names: NameGenerator | None = None,
    ) -> None:
        self._rng = rng or random.Random()
        # Comparte el mismo rng con el generador de nombres para mantener el
        # determinismo en una sola cadena de azar.
        self._names = names or NameGenerator(self._rng)

    def generate(self, position: Position | None = None) -> Player:
        """Genera un jugador; si no se da `position`, se elige al azar."""
        rng = self._rng
        pos = position or rng.choice(list(Position))
        return Player(
            name=self._names.player_name(),
            age=rng.randint(16, 38),
            position=pos,
            # El pie derecho es el mas comun; ambos, el mas raro.
            foot=rng.choices(list(Foot), weights=[3, 6, 1])[0],
            pace=rng.randint(40, 90),
            shooting=rng.randint(40, 90),
            passing=rng.randint(40, 90),
            defending=rng.randint(40, 90),
            physical=rng.randint(40, 90),
        )
