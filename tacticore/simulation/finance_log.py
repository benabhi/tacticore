"""Libro de caja del club del jugador (movimientos en tiempo real).

La economia se refleja apenas ocurre: cuando entra o sale dinero se registra un
`Movement` (fecha, concepto, monto con signo) en `club.movements`. Solo el club
del jugador lleva libro (a la IA no le hace falta). La UI lo muestra en Finanzas >
Movimientos. Funciones puras sobre el estado (sin UI).
"""

from datetime import date

from ..domain.club import Club
from ..domain.movement import Movement

# Tope de movimientos guardados (se descartan los mas viejos).
_MAX = 200


def record_movement(club: Club, when: date, concept: str, amount: int) -> None:
    """Anota un movimiento en el libro del club (positivo = ingreso, negativo = gasto)."""
    if amount == 0:
        return
    club.movements.append(Movement(date=when, concept=concept, amount=amount))
    if len(club.movements) > _MAX:
        del club.movements[: len(club.movements) - _MAX]


def newest_first(club: Club) -> list[Movement]:
    """Los movimientos del mas nuevo al mas viejo (para la lista de la UI)."""
    return list(reversed(club.movements))
