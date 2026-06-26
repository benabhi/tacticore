"""Generador de presidentes de fantasia.

Un presidente tiene identidad: nombre y apellido (por nacionalidad, del mismo
pool que los jugadores), nacionalidad y edad. Los presidentes son mayores: la
edad arranca en 45 o mas. Determinista: comparte el rng del juego.
"""

import random
from datetime import date

from .. import config
from ..domain.president import President
from ._people import birth_date_for_age
from .name_generator import NameGenerator

# Rango de edad de un presidente al generarlo (gente grande).
_MIN_AGE = 45
_MAX_AGE = 75


class PresidentGenerator:
    """Crea presidentes con nombre, nacionalidad y edad (>= 45)."""

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
    ) -> President:
        """Genera un presidente de la nacionalidad `country_code`."""
        today = today or config.SEASON_START_DATE
        first, last = self._names.player_first_last(country_code)
        target_age = self._rng.randint(_MIN_AGE, _MAX_AGE)
        birth_date = birth_date_for_age(self._rng, today, target_age)
        return President(
            first_name=first,
            last_name=last,
            nationality=country_code or "FAN",
            birth_date=birth_date,
        )
