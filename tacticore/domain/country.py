"""Entidad Pais.

Los paises usan nombres reales (Argentina, Brasil, ...) como contenedores;
los clubes y jugadores que viven adentro son de fantasia. Cada pais tiene 5
ligas (niveles A a E).
"""

from dataclasses import dataclass, field

from .league import League


@dataclass
class Country:
    """Un pais con sus ligas."""

    name: str
    code: str  # codigo corto ASCII, ej. "ARG"
    leagues: list[League] = field(default_factory=list)
