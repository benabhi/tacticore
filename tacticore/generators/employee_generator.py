"""Generador de empleados del cuerpo de trabajo (medico, director financiero, ...).

Identidad del pool de nombres y una edad de adulto. Cada empleado lleva 1-3 BONUS: el
primario del rol (fuerza sesgada por el nivel de liga, con ruido) mas 0-2 extras
SORTEADOS de la bolsa de SU rol (mas debiles). El sueldo se fija con `staff.staff_wage`
segun el PODER total (fuente unica). Los candidatos que se ofrecen al contratar
(`candidates`) vienen en variantes para que la eleccion importe. Determinista: comparte
el rng que se le pasa.
"""

import random
from datetime import date

from .. import config
from ..domain.employee import Employee
from ..domain.enums import BonusType, EmployeeRole, LeagueTier
from ..simulation.staff import role_extras, role_primary, staff_wage
from ._people import birth_date_for_age
from .name_generator import NameGenerator

# Peso de la cantidad de bonus EXTRA (0/1/2): la mayoria trae 1, algunos 2, pocos 0.
_EXTRA_COUNT_WEIGHTS = (0.30, 0.45, 0.25)

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

    def _bonuses(self, role: EmployeeRole, primary_strength: float) -> dict[BonusType, float]:
        """Bonus del empleado: primario del rol + 0-2 extras de la bolsa de su rol."""
        rng = self._rng
        bonuses = {role_primary(role): _clamp(primary_strength)}
        n_extra = rng.choices((0, 1, 2), weights=_EXTRA_COUNT_WEIGHTS)[0]
        pool = [t for t in role_extras(role)]
        rng.shuffle(pool)
        for t in pool[:n_extra]:
            bonuses[t] = _clamp(primary_strength * rng.uniform(0.4, 0.7))
        return bonuses

    def _make(
        self,
        role: EmployeeRole,
        country_code: str | None,
        tier: LeagueTier,
        today: date,
        primary_strength: float,
    ) -> Employee:
        rng = self._rng
        first, last = self._names.player_first_last(country_code)
        age = rng.randint(_MIN_AGE, _MAX_AGE)
        birth_date = birth_date_for_age(rng, today, age)
        bonuses = self._bonuses(role, primary_strength)
        power = sum(bonuses.values())
        return Employee(
            role=role,
            first_name=first,
            last_name=last,
            nationality=country_code or "FAN",
            birth_date=birth_date,
            bonuses=bonuses,
            weekly_wage=staff_wage(power, tier),
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
