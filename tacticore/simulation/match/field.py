"""Modelo de la cancha (continuo, en metros) y mapeo a celdas de render.

Sistema de coordenadas (metros):
- eje x a lo largo, de arco a arco: 0 (arco "home") .. length (arco "away").
- eje y a lo ancho: 0 .. width.

Los jugadores y la pelota viven en estas coordenadas continuas (float). El
render mapea metros -> celdas con `GridMap`. Ver docs/DESIGN.md seccion 4.
"""

from __future__ import annotations

from dataclasses import dataclass

from .geometry import Rect, Vec2

# Medidas estandar de una cancha (metros).
_PENALTY_AREA_DEPTH = 16.5
_PENALTY_AREA_WIDTH = 40.3
_GOAL_AREA_DEPTH = 5.5
_GOAL_AREA_WIDTH = 18.32
_CENTER_CIRCLE_RADIUS = 9.15
_PENALTY_SPOT_DIST = 11.0


@dataclass(frozen=True)
class Pitch:
    """La cancha en coordenadas continuas (metros)."""

    length: float = 105.0
    width: float = 68.0

    @property
    def bounds(self) -> Rect:
        """Rectangulo de toda la cancha."""
        return Rect(0.0, 0.0, self.length, self.width)

    @property
    def center(self) -> Vec2:
        """Punto central (de saque)."""
        return Vec2(self.length / 2, self.width / 2)

    @property
    def center_circle_radius(self) -> float:
        return _CENTER_CIRCLE_RADIUS

    @property
    def home_goal(self) -> Vec2:
        """Centro del arco propio (x = 0)."""
        return Vec2(0.0, self.width / 2)

    @property
    def away_goal(self) -> Vec2:
        """Centro del arco rival (x = length)."""
        return Vec2(self.length, self.width / 2)

    def penalty_area(self, home: bool) -> Rect:
        """Area grande (penal) de un lado de la cancha."""
        y = (self.width - _PENALTY_AREA_WIDTH) / 2
        if home:
            return Rect(0.0, y, _PENALTY_AREA_DEPTH, _PENALTY_AREA_WIDTH)
        return Rect(
            self.length - _PENALTY_AREA_DEPTH, y, _PENALTY_AREA_DEPTH, _PENALTY_AREA_WIDTH
        )

    def goal_area(self, home: bool) -> Rect:
        """Area chica (de meta) de un lado de la cancha."""
        y = (self.width - _GOAL_AREA_WIDTH) / 2
        if home:
            return Rect(0.0, y, _GOAL_AREA_DEPTH, _GOAL_AREA_WIDTH)
        return Rect(
            self.length - _GOAL_AREA_DEPTH, y, _GOAL_AREA_DEPTH, _GOAL_AREA_WIDTH
        )

    def penalty_spot(self, home: bool) -> Vec2:
        """Punto de penal de un lado."""
        if home:
            return Vec2(_PENALTY_SPOT_DIST, self.width / 2)
        return Vec2(self.length - _PENALTY_SPOT_DIST, self.width / 2)

    def contains(self, point: Vec2) -> bool:
        """Si el punto esta dentro de la cancha."""
        return self.bounds.contains(point)

    def clamp(self, point: Vec2) -> Vec2:
        """Acota un punto a los limites de la cancha."""
        return self.bounds.clamp(point)


@dataclass(frozen=True)
class GridMap:
    """Convierte coordenadas de cancha (metros) <-> celdas (col, row).

    `cols` x `rows` es el tamano de la grilla de render (el area jugable del
    widget). Una celda cubre un rectangulo de cancha; `to_meters` devuelve el
    centro de la celda.
    """

    cols: int
    rows: int
    pitch: Pitch

    def to_cell(self, point: Vec2) -> tuple[int, int]:
        """Metros -> (col, row), acotado a la grilla."""
        col = int(point.x / self.pitch.length * self.cols)
        row = int(point.y / self.pitch.width * self.rows)
        col = min(max(col, 0), self.cols - 1)
        row = min(max(row, 0), self.rows - 1)
        return col, row

    def to_meters(self, col: int, row: int) -> Vec2:
        """(col, row) -> metros (centro de la celda)."""
        x = (col + 0.5) / self.cols * self.pitch.length
        y = (row + 0.5) / self.rows * self.pitch.width
        return Vec2(x, y)
