"""Generador de directores tecnicos de fantasia (uno por club).

Un DT es un adulto de 35+ (suele ser un ex-jugador). Su identidad sale del mismo
pool de nombres que los jugadores; su habilidad se sesga por el nivel de la liga
(mejores ligas -> mejores DTs), mientras que el liderazgo es mas independiente de
la categoria. Determinista: comparte el rng del juego. Escala 1-100 con decimales.
"""

import random
from datetime import date

from .. import config
from ..domain.coach import Coach
from ..domain.enums import LeagueTier, Mentality
from ._people import birth_date_for_age
from .name_generator import NameGenerator

# Rango de edad del DT (adulto; suele ser ex-jugador, nunca un pibe).
_MIN_AGE, _MAX_AGE = 35, 68

# Habilidad base segun el nivel de liga (misma escala/valores que los jugadores).
_TIER_SKILL: dict[LeagueTier, float] = {
    LeagueTier.A: 78.0,
    LeagueTier.B: 66.0,
    LeagueTier.C: 54.0,
    LeagueTier.D: 44.0,
    LeagueTier.E: 35.0,
}
_SKILL_NOISE = 8.0  # variacion de habilidad dentro de una misma liga (+/-)


def _clamp(value: float) -> float:
    """Acota a 1.0-100.0 y redondea a un decimal (como los atributos)."""
    return round(max(1.0, min(100.0, value)), 1)


class CoachGenerator:
    """Crea directores tecnicos con identidad, mentalidad, habilidad y liderazgo."""

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
        tier: LeagueTier = LeagueTier.E,
        today: date | None = None,
        mentality: Mentality | None = None,
    ) -> Coach:
        """Genera un DT de la nacionalidad `country_code` para una liga `tier`.

        `today` (fecha del juego) ancla la fecha de nacimiento para que la edad
        sea >= 35 al inicio y el DT envejezca al avanzar el calendario. Si se pasa
        `mentality`, la usa (el DT del club del jugador lo elige el jugador); si no,
        la sortea.
        """
        today = today or config.SEASON_START_DATE
        rng = self._rng
        first, last = self._names.player_first_last(country_code)
        age = rng.randint(_MIN_AGE, _MAX_AGE)
        birth_date = birth_date_for_age(rng, today, age)
        skill = _clamp(_TIER_SKILL[tier] + rng.uniform(-_SKILL_NOISE, _SKILL_NOISE))
        leadership = _clamp(rng.uniform(30, 90))
        return Coach(
            first_name=first,
            last_name=last,
            nationality=country_code or "FAN",
            birth_date=birth_date,
            mentality=mentality if mentality is not None else rng.choice(list(Mentality)),
            skill=skill,
            leadership=leadership,
        )
