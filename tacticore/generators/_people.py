"""Helpers compartidos para generar personas (DT, presidentes, ...).

Aca vive la logica comun a varios generadores de "personas" para no duplicarla.
"""

import random
from datetime import date


def birth_date_for_age(rng: random.Random, today: date, age: int) -> date:
    """Devuelve una fecha de nacimiento que da EXACTAMENTE `age` anios a `today`.

    El mes/dia salen al azar (cumpleanios repartidos por todo el calendario); el
    anio de nacimiento depende de si el cumpleanios de este anio ya paso o no, asi
    la edad cumplida queda garantizada.
    """
    month, day = rng.randint(1, 12), rng.randint(1, 28)
    birth_year = today.year - age
    if (month, day) > (today.month, today.day):
        birth_year -= 1
    return date(birth_year, month, day)
