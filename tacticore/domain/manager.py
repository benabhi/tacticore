"""Entidad Manager (director tecnico / DT).

Es quien dirige al equipo en los partidos y tendra un papel importante en el
juego. NO confundir con el presidente (ese es el jugador). Por ahora guarda solo
identidad basica (nombre, nacionalidad, fecha de nacimiento); mas adelante
sumara atributos (tactica, motivacion, gestion de vestuario, etc.).
"""

from dataclasses import dataclass
from datetime import date


@dataclass
class Manager:
    """El director tecnico de un club."""

    first_name: str
    last_name: str
    nationality: str     # codigo de pais ISO alpha2 (ej. "AR")
    birth_date: date     # la edad se calcula contra la fecha del juego

    @property
    def full_name(self) -> str:
        """Nombre y apellido."""
        return f"{self.first_name} {self.last_name}"

    def age_on(self, today: date) -> int:
        """Edad en anios cumplidos a la fecha `today` (la del juego)."""
        years = today.year - self.birth_date.year
        if (today.month, today.day) < (self.birth_date.month, self.birth_date.day):
            years -= 1
        return years
