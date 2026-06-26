"""Entidad Presidente (el maximo dirigente de un club).

El presidente del club del jugador es el propio jugador; los demas clubes tienen
presidentes generados. No confundir con el Manager (DT), que dirige al equipo en
los partidos. Por ahora guarda solo identidad basica; mas adelante sumara gestion
(finanzas, paciencia, ambicion, etc.).

`birth_date` es opcional: del presidente humano no pedimos la edad, asi que queda
en None.
"""

from dataclasses import dataclass
from datetime import date


@dataclass
class President:
    """El presidente de un club."""

    first_name: str
    last_name: str
    nationality: str          # codigo de pais ISO alpha2 (ej. "AR")
    birth_date: date | None = None  # None si no se conoce (presidente humano)

    @property
    def full_name(self) -> str:
        """Nombre y apellido."""
        return f"{self.first_name} {self.last_name}".strip()

    def age_on(self, today: date) -> int | None:
        """Edad en anios cumplidos a la fecha `today`, o None si no hay fecha."""
        if self.birth_date is None:
            return None
        years = today.year - self.birth_date.year
        if (today.month, today.day) < (self.birth_date.month, self.birth_date.day):
            years -= 1
        return years
