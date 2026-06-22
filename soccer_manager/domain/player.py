"""Entidad Jugador."""

from dataclasses import dataclass

from .enums import Foot, Position


@dataclass
class Player:
    """Un jugador del juego.

    Los atributos van de 1 a 99 (estilo manager clasico). `overall` es una
    media simple; mas adelante puede ponderarse segun la posicion.
    """

    name: str
    age: int
    position: Position
    foot: Foot

    # Atributos principales (1-99).
    pace: int = 50
    shooting: int = 50
    passing: int = 50
    defending: int = 50
    physical: int = 50

    @property
    def overall(self) -> int:
        """Media simple de los atributos principales."""
        attrs = (
            self.pace,
            self.shooting,
            self.passing,
            self.defending,
            self.physical,
        )
        return round(sum(attrs) / len(attrs))
