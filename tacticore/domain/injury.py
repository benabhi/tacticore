"""Entidad Lesion."""

from dataclasses import dataclass
from datetime import date

from .enums import InjurySeverity, InjuryType


@dataclass
class Injury:
    """Una lesion concreta de un jugador, con su ventana de baja."""

    type: InjuryType
    severity: InjurySeverity
    start_date: date
    expected_return: date

    def is_active_on(self, day: date) -> bool:
        """Indica si la lesion sigue activa en la fecha dada."""
        return self.start_date <= day < self.expected_return

    def days_out(self) -> int:
        """Dias totales de baja previstos."""
        return (self.expected_return - self.start_date).days
