"""Entidad Coach (director tecnico del club).

El director tecnico dirige al equipo en lo futbolistico. Es distinto del
`Manager` (el rol del jugador, tipo presidente/manager de la institucion): cada
club tiene SU director tecnico. Suele ser un ex-jugador o al menos un adulto de
35+ anios.

Guarda identidad (nombre, nacionalidad, fecha de nacimiento) y tres rasgos que
consumira la simulacion:
- `mentality`: sesgo tactico por defecto (reusa el enum de las tacticas).
- `skill`: habilidad (1-100), impactara la formula de entrenamiento.
- `leadership`: liderazgo (1-100), influira en la moral del plantel.

`skill`/`leadership` van en escala 1-100 con decimales, como los atributos de los
jugadores (ver docs/DESIGN.md).
"""

from dataclasses import dataclass
from datetime import date

from .enums import Mentality


@dataclass
class Coach:
    """El director tecnico de un club."""

    first_name: str
    last_name: str
    nationality: str                # codigo de pais ISO alpha2 (ej. "AR")
    birth_date: date                # la edad se calcula contra la fecha del juego
    mentality: Mentality = Mentality.NEUTRAL
    skill: float = 1.0              # habilidad (1-100): calidad del entrenamiento
    leadership: float = 1.0         # liderazgo (1-100): influye en la moral

    @property
    def full_name(self) -> str:
        """Nombre y apellido."""
        return f"{self.first_name} {self.last_name}".strip()

    def age_on(self, today: date) -> int:
        """Edad en anios cumplidos a la fecha `today` (la del juego)."""
        years = today.year - self.birth_date.year
        if (today.month, today.day) < (self.birth_date.month, self.birth_date.day):
            years -= 1
        return years
