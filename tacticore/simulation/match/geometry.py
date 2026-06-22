"""Primitivas geometricas 2D para la simulacion (sin UI).

`Vec2` es un punto/vector 2D inmutable con las operaciones que necesita el
movimiento (steering): suma, resta, escala, modulo, normalizar, acotar. `Rect`
es una region rectangular en metros (para zonas y areas).
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Vec2:
    """Vector / punto 2D inmutable (en metros)."""

    x: float
    y: float

    def __add__(self, other: Vec2) -> Vec2:
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vec2) -> Vec2:
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Vec2:
        return Vec2(self.x * scalar, self.y * scalar)

    __rmul__ = __mul__

    def length_sq(self) -> float:
        """Modulo al cuadrado (evita la raiz; util para comparar distancias)."""
        return self.x * self.x + self.y * self.y

    def length(self) -> float:
        """Modulo (longitud) del vector."""
        return math.sqrt(self.length_sq())

    def distance_to(self, other: Vec2) -> float:
        """Distancia a otro punto."""
        return (self - other).length()

    def normalized(self) -> Vec2:
        """Vector unitario en la misma direccion (o (0,0) si es nulo)."""
        n = self.length()
        if n == 0.0:
            return Vec2(0.0, 0.0)
        return Vec2(self.x / n, self.y / n)

    def clamped(self, max_length: float) -> Vec2:
        """Acota el modulo a `max_length` sin cambiar la direccion."""
        n = self.length()
        if n <= max_length or n == 0.0:
            return self
        scale = max_length / n
        return Vec2(self.x * scale, self.y * scale)

    def dot(self, other: Vec2) -> float:
        """Producto punto."""
        return self.x * other.x + self.y * other.y


@dataclass(frozen=True)
class Rect:
    """Region rectangular en metros (esquina inferior-izquierda + tamano)."""

    x: float
    y: float
    width: float
    height: float

    @property
    def max_x(self) -> float:
        return self.x + self.width

    @property
    def max_y(self) -> float:
        return self.y + self.height

    @property
    def center(self) -> Vec2:
        return Vec2(self.x + self.width / 2, self.y + self.height / 2)

    def contains(self, point: Vec2) -> bool:
        """Si el punto cae dentro del rectangulo (bordes incluidos)."""
        return self.x <= point.x <= self.max_x and self.y <= point.y <= self.max_y

    def clamp(self, point: Vec2) -> Vec2:
        """Devuelve el punto acotado a los limites del rectangulo."""
        return Vec2(
            min(max(point.x, self.x), self.max_x),
            min(max(point.y, self.y), self.max_y),
        )
