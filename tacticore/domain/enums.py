"""Enumeraciones del dominio (posiciones, pie habil, etc.)."""

from enum import Enum


class Position(Enum):
    """Posicion principal de un jugador en el campo."""

    GOALKEEPER = "GK"
    DEFENDER = "DEF"
    MIDFIELDER = "MID"
    FORWARD = "FWD"


class Foot(Enum):
    """Pie habil de un jugador."""

    LEFT = "L"
    RIGHT = "R"
    BOTH = "B"
