"""Entidad Employee (empleado del cuerpo de trabajo del club).

Aparte del `Coach` (director tecnico), un club puede contratar empleados de
distintos roles (`EmployeeRole`): medico, director financiero, etc. Cada empleado
guarda su identidad (nombre, nacionalidad, fecha de nacimiento) y una unica
habilidad `skill` (1-100) que es la fuente de verdad: maneja tanto la fuerza de su
bonus como el `weekly_wage` (sueldo semanal), que se fija al contratarlo y actua de
barrera economica. La escala 1-100 es la misma que la del DT y los jugadores (una
sola forma de leer la competencia). La logica de sueldos, cupos y efectos vive en
`simulation/staff.py`.
"""

from dataclasses import dataclass
from datetime import date

from .enums import EmployeeRole


@dataclass
class Employee:
    """Un empleado del cuerpo de trabajo (distinto del DT)."""

    role: EmployeeRole
    first_name: str
    last_name: str
    nationality: str                # codigo de pais ISO alpha2 (ej. "AR")
    birth_date: date                # la edad se calcula contra la fecha del juego
    skill: float = 1.0              # habilidad (1-100): fuerza del bonus y del sueldo
    weekly_wage: int = 0            # sueldo semanal fijado al contratar (barrera)

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
