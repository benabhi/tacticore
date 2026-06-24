"""Motor de partido en tiempo real (sin UI).

Por ahora: modelo geometrico de la cancha (geometry/field), entidades y estado
inicial (entities/formation/state). El tick determinista y la IA llegan en los
proximos pasos de la Fase B (ver docs/DESIGN.md).
"""

from .commands import Command, SetPlayerZone
from .engine import DEFAULT_DT, MatchEngine
from .entities import Ball, MatchPlayer, Referee, Role, Side
from .events import MatchEvent
from .field import GridMap, Pitch
from .formation import (
    DEFAULT_FORMATIONS,
    FORMATION_11,
    FORMATION_11_442,
    FORMATIONS_11,
    Formation,
    FormationSlot,
)
from .geometry import Rect, Vec2
from .state import MatchPhase, MatchState, kickoff_state

__all__ = [
    "Ball",
    "Command",
    "DEFAULT_DT",
    "DEFAULT_FORMATIONS",
    "FORMATION_11",
    "FORMATION_11_442",
    "FORMATIONS_11",
    "Formation",
    "FormationSlot",
    "GridMap",
    "MatchEngine",
    "MatchEvent",
    "MatchPhase",
    "MatchPlayer",
    "MatchState",
    "Pitch",
    "Rect",
    "Referee",
    "Role",
    "SetPlayerZone",
    "Side",
    "Vec2",
    "kickoff_state",
]
