"""Motor de partido en tiempo real (sin UI).

Por ahora: modelo geometrico de la cancha (geometry/field), entidades y estado
inicial (entities/formation/state). El tick determinista y la IA llegan en los
proximos pasos de la Fase B (ver docs/DESIGN.md).
"""

from .engine import DEFAULT_DT, MatchEngine
from .entities import Ball, MatchPlayer, Side
from .field import GridMap, Pitch
from .formation import DEFAULT_FORMATIONS, Formation, FormationSlot
from .geometry import Rect, Vec2
from .state import MatchPhase, MatchState, kickoff_state

__all__ = [
    "Ball",
    "DEFAULT_DT",
    "DEFAULT_FORMATIONS",
    "Formation",
    "FormationSlot",
    "GridMap",
    "MatchEngine",
    "MatchPhase",
    "MatchPlayer",
    "MatchState",
    "Pitch",
    "Rect",
    "Side",
    "Vec2",
    "kickoff_state",
]
