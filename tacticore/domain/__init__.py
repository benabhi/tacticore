"""Entidades puras del dominio (dataclasses), sin logica de UI ni simulacion."""

from .club import Club
from .country import Country
from .enums import (
    Foot,
    InjurySeverity,
    InjuryType,
    LeagueTier,
    Morale,
    Position,
    Specialty,
)
from .injury import Injury
from .league import League
from .player import Player
from .stadium import Stadium

__all__ = [
    "Club",
    "Country",
    "Foot",
    "Injury",
    "InjurySeverity",
    "InjuryType",
    "League",
    "LeagueTier",
    "Morale",
    "Player",
    "Position",
    "Specialty",
    "Stadium",
]
