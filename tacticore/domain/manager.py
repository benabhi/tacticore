"""Entidad Manager (el director del club; en un juego de manager, sos vos).

Es quien dirige al club: el del club del jugador es el propio jugador; los demas
clubes tienen managers generados. Por ahora guarda solo identidad basica (nombre,
nacionalidad y, si se conoce, fecha de nacimiento); mas adelante sumara atributos
(tactica, motivacion, gestion de vestuario, etc.).

`birth_date` es opcional: del manager humano no pedimos la edad, asi que queda en
None.
"""

from dataclasses import dataclass
from datetime import date


@dataclass
class Manager:
    """El director de un club."""

    first_name: str
    last_name: str
    nationality: str                # codigo de pais ISO alpha2 (ej. "AR")
    birth_date: date | None = None  # None si no se conoce (manager humano)

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
