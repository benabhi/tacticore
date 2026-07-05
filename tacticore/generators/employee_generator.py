"""Generador de empleados del cuerpo de trabajo (medico, director financiero, ...).

Mismo molde que el `CoachGenerator`: identidad del pool de nombres, habilidad
sesgada por el nivel de liga (mejor liga -> mejores empleados) con ruido, y una
edad de adulto. El sueldo se fija con `staff.staff_wage` (fuente unica). Los
candidatos que se ofrecen al contratar (`candidates`) vienen en variantes para que
la eleccion importe: uno barato flojo, uno medio, uno caro competente. Determinista:
comparte el rng que se le pasa.
"""

import random
from datetime import date

from .. import config
from ..domain.employee import Employee
from ..domain.enums import EmployeeRole, LeagueTier
from ..simulation.staff import staff_wage
from ._people import birth_date_for_age
from .name_generator import NameGenerator

# Rango de edad de un empleado (adulto profesional).
_MIN_AGE, _MAX_AGE = 30, 63

# Habilidad base por nivel de liga (misma escala que DTs/jugadores).
_TIER_SKILL: dict[LeagueTier, float] = {
    LeagueTier.A: 78.0,
    LeagueTier.B: 66.0,
    LeagueTier.C: 54.0,
    LeagueTier.D: 44.0,
    LeagueTier.E: 35.0,
}
_SKILL_NOISE = 8.0  # variacion dentro de una misma liga (+/-)


def _clamp(value: float) -> float:
    """Acota a 1.0-100.0 y redondea a un decimal."""
    return round(max(1.0, min(100.0, value)), 1)


class EmployeeGenerator:
    """Crea empleados con identidad, habilidad y sueldo acorde al nivel del club."""

    def __init__(
        self,
        rng: random.Random | None = None,
        names: NameGenerator | None = None,
    ) -> None:
        self._rng = rng or random.Random()
        self._names = names or NameGenerator(self._rng)

    def _make(
        self,
        role: EmployeeRole,
        country_code: str | None,
        tier: LeagueTier,
        today: date,
        skill: float,
    ) -> Employee:
        rng = self._rng
        first, last = self._names.player_first_last(country_code)
        age = rng.randint(_MIN_AGE, _MAX_AGE)
        birth_date = birth_date_for_age(rng, today, age)
        skill = _clamp(skill)
        return Employee(
            role=role,
            first_name=first,
            last_name=last,
            nationality=country_code or "FAN",
            birth_date=birth_date,
            skill=skill,
            weekly_wage=staff_wage(role, skill, tier),
        )

    def generate(
        self,
        role: EmployeeRole,
        country_code: str | None = None,
        tier: LeagueTier = LeagueTier.E,
        today: date | None = None,
    ) -> Employee:
        """Genera un empleado del rol y nivel de liga dados."""
        today = today or config.SEASON_START_DATE
        skill = _TIER_SKILL[tier] + self._rng.uniform(-_SKILL_NOISE, _SKILL_NOISE)
        return self._make(role, country_code, tier, today, skill)

    def candidates(
        self,
        role: EmployeeRole,
        tier: LeagueTier = LeagueTier.E,
        country_code: str | None = None,
        today: date | None = None,
        n: int = 3,
    ) -> list[Employee]:
        """Devuelve `n` candidatos variados para contratar (skill/edad/sueldo distintos)."""
        today = today or config.SEASON_START_DATE
        base = _TIER_SKILL[tier]
        # Sesgos de habilidad: flojo/barato, medio, competente/caro.
        biases = [-_SKILL_NOISE, 0.0, _SKILL_NOISE]
        out: list[Employee] = []
        for i in range(n):
            bias = biases[i % len(biases)]
            skill = base + bias + self._rng.uniform(-3.0, 3.0)
            out.append(self._make(role, country_code, tier, today, skill))
        return out
