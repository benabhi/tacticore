"""Generador de directores tecnicos (DT) de fantasia.

Por ahora un DT tiene solo identidad: nombre y apellido (por nacionalidad, del
mismo pool que los jugadores), nacionalidad y edad. La edad arranca siempre en
40 o mas (un DT no es un pibe). Determinista: comparte el rng del juego.
"""

import random
from datetime import date

from .. import config
from ..domain.manager import Manager
from .name_generator import NameGenerator

# Rango de edad de un DT al generarlo (siempre adulto mayor de 40).
_MIN_AGE = 40
_MAX_AGE = 65


class ManagerGenerator:
    """Crea directores tecnicos con nombre, nacionalidad y edad (>= 40)."""

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
        """Genera un DT de la nacionalidad `country_code`.

        `today` (fecha del juego) ancla la fecha de nacimiento para que la edad
        sea >= 40 al inicio y el DT envejezca al avanzar el calendario.
        """
        today = today or config.SEASON_START_DATE
        first, last = self._names.player_first_last(country_code)
        # Edad EXACTA = target_age (>= 40). El anio de nacimiento depende de si el
        # cumpleanios de este anio ya paso o no, asi la edad queda garantizada y
        # los cumpleanios se reparten por todo el calendario.
        target_age = self._rng.randint(_MIN_AGE, _MAX_AGE)
        month, day = self._rng.randint(1, 12), self._rng.randint(1, 28)
        birth_year = today.year - target_age
        if (month, day) > (today.month, today.day):
            birth_year -= 1
        birth_date = date(birth_year, month, day)
        return Manager(
            first_name=first,
            last_name=last,
            nationality=country_code or "FAN",
            birth_date=birth_date,
        )
