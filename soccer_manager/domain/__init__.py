"""Entidades puras del dominio (dataclasses), sin logica de UI ni simulacion."""

from .club import Club
from .enums import Foot, Position
from .player import Player

__all__ = ["Club", "Foot", "Position", "Player"]
