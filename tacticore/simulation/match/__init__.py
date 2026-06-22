"""Motor de partido en tiempo real (sin UI).

Por ahora solo el modelo geometrico de la cancha. El estado, las entidades, el
tick determinista y la IA llegan en la Fase B (ver docs/DESIGN.md).
"""

from .field import GridMap, Pitch
from .geometry import Rect, Vec2

__all__ = ["GridMap", "Pitch", "Rect", "Vec2"]
