"""Entidades puras del dominio (dataclasses), sin logica de UI ni simulacion."""

from .club import Club
from .enums import (
    Foot,
    InjurySeverity,
    InjuryType,
    Morale,
    Position,
    Specialty,
)
from .injury import Injury
from .player import Player
from .skills import skill_level_name

__all__ = [
    "Club",
    "Foot",
    "Injury",
    "InjurySeverity",
    "InjuryType",
    "Morale",
    "Player",
    "Position",
    "Specialty",
    "skill_level_name",
]
