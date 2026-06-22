"""Calendario del juego y avance de fechas.

El juego progresa avanzando dias/jornadas; al pasar fechas se disparan los
calculos (partidos, finanzas, etc.). Este modulo solo lleva la cuenta del
tiempo; los calculos viven en `simulation/`.
"""

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class GameCalendar:
    """Lleva la fecha actual de la partida."""

    current_date: date

    def advance(self, days: int = 1) -> date:
        """Avanza `days` dias y devuelve la nueva fecha actual."""
        self.current_date += timedelta(days=days)
        return self.current_date
