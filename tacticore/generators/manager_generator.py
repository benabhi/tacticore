"""Generador de managers de fantasia (los que dirigen los clubes IA).

Por ahora un manager tiene solo identidad: nombre y apellido (por nacionalidad,
del mismo pool que los jugadores), nacionalidad y edad. La edad arranca siempre
en 40 o mas (un manager no es un pibe). Determinista: comparte el rng del juego.
"""

import random
from datetime import date

from .. import config
from ..domain.manager import Manager
from ._people import birth_date_for_age
from .name_generator import NameGenerator

# Rango de edad de un manager al generarlo (siempre adulto mayor de 40).
_MIN_AGE = 40
_MAX_AGE = 65


class ManagerGenerator:
    """Crea managers con nombre, nacionalidad y edad (>= 40)."""

    def __init__(
        self,
        rng: random.Random | None = None,
        names: NameGenerator | None = None,
    ) -> None:
        self._rng = rng or random.Random()
        self._names = names or NameGenerator(self._rng)

    def generate(
        self,
        country_code: str | None = None,
        today: date | None = None,
    ) -> Manager:
        """Genera un manager de la nacionalidad `country_code`.

        `today` (fecha del juego) ancla la fecha de nacimiento para que la edad
        sea >= 40 al inicio y el manager envejezca al avanzar el calendario.
        """
        today = today or config.SEASON_START_DATE
        first, last = self._names.player_first_last(country_code)
        # Edad EXACTA garantizada (>= 40), con cumpleanios repartidos en el anio.
        target_age = self._rng.randint(_MIN_AGE, _MAX_AGE)
        birth_date = birth_date_for_age(self._rng, today, target_age)
        return Manager(
            first_name=first,
            last_name=last,
            nationality=country_code or "FAN",
            birth_date=birth_date,
        )
