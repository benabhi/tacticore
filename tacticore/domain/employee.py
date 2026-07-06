"""Entidad Employee (empleado del cuerpo de trabajo del club).

Aparte del `Coach` (director tecnico), un club puede contratar empleados de
distintos roles (`EmployeeRole`): medico, director financiero, etc. Cada empleado
guarda su identidad (nombre, nacionalidad, fecha de nacimiento) y hasta **3 bonus**
(`bonuses`: tipo -> fuerza 1-100): el del rol (primario) mas 0-2 extra, para armar
"builds". El `weekly_wage` (sueldo semanal, barrera economica) escala con el PODER
total (suma de fuerzas). La logica de sueldos, cupos y efectos vive en
`simulation/staff.py`.
"""

from dataclasses import dataclass, field
from datetime import date

from .enums import BonusType, EmployeeRole


@dataclass
class Employee:
    """Un empleado del cuerpo de trabajo (distinto del DT)."""

    role: EmployeeRole
    first_name: str
    last_name: str
    nationality: str                # codigo de pais ISO alpha2 (ej. "AR")
    birth_date: date                # la edad se calcula contra la fecha del juego
    bonuses: dict[BonusType, float] = field(default_factory=dict)  # 1-3 bonus (tipo->fuerza)
    weekly_wage: int = 0            # sueldo semanal fijado al contratar (barrera)

    @property
    def full_name(self) -> str:
        """Nombre y apellido."""
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def power(self) -> float:
        """Poder total del empleado: suma de las fuerzas de sus bonus (para el sueldo)."""
        return sum(self.bonuses.values())

    def age_on(self, today: date) -> int:
        """Edad en anios cumplidos a la fecha `today` (la del juego)."""
        years = today.year - self.birth_date.year
        if (today.month, today.day) < (self.birth_date.month, self.birth_date.day):
            years -= 1
        return years
