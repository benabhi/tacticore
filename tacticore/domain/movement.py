"""Entidad Movimiento: una linea del libro de caja del club del jugador.

La economia es en tiempo real: cada vez que entra o sale dinero (taquilla de un
partido, sueldos de la semana, un fichaje, el patrocinador...) se registra un
movimiento con su fecha, concepto y monto (positivo = ingreso, negativo = gasto).
Se muestran en Finanzas > Movimientos. Solo el club del jugador lleva libro.
"""

from dataclasses import dataclass
from datetime import date


@dataclass
class Movement:
    """Un ingreso (+) o gasto (-) del club, con fecha y concepto."""

    date: date
    concept: str
    amount: int  # positivo = ingreso, negativo = gasto
