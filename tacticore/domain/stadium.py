"""Entidad Estadio.

Por ahora basico (nombre y capacidad). Mas adelante le vamos a sumar mejoras
e instalaciones para recaudar dinero (tiendas, palcos, etc.).
"""

from dataclasses import dataclass


@dataclass
class Stadium:
    """El estadio de un club."""

    name: str
    capacity: int
    # TODO: mejoras / instalaciones que generan ingresos.
