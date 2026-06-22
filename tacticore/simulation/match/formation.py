"""Formaciones: como se ubican los jugadores en la cancha.

Una formacion es una lista de "slots" (posicion + ubicacion relativa). Las
coordenadas relativas son 0..1: `rel_x` va de 0 (arco propio) a 1 (arco rival),
`rel_y` de 0 a 1 a lo ancho. Se mapean a metros y se espejan para el visitante.

Por ahora el motor arranca con 7v7 (config de prueba); todo queda parametrizado
por formacion para escalar a 11 mas adelante (ver docs/DESIGN.md).
"""

from dataclasses import dataclass

from ...domain.club import Club
from ...domain.enums import Position
from ...domain.player import Player
from .entities import Side
from .field import Pitch
from .geometry import Vec2


@dataclass(frozen=True)
class FormationSlot:
    """Un puesto de la formacion: posicion natural + ubicacion relativa."""

    position: Position
    rel_x: float  # 0 = arco propio, 1 = arco rival
    rel_y: float  # 0..1 a lo ancho


@dataclass(frozen=True)
class Formation:
    """Una formacion (su cantidad de slots define el tamano del equipo)."""

    name: str
    slots: tuple[FormationSlot, ...]

    @property
    def size(self) -> int:
        return len(self.slots)


def _slot(position: Position, rel_x: float, rel_y: float) -> FormationSlot:
    return FormationSlot(position, rel_x, rel_y)

# Formacion 7v7 (1-2-3-1): config de prueba inicial del motor.
FORMATION_7 = Formation(
    "1-2-3-1",
    (
        _slot(Position.GOALKEEPER, 0.05, 0.50),
        _slot(Position.DEFENDER, 0.22, 0.30),
        _slot(Position.DEFENDER, 0.22, 0.70),
        _slot(Position.MIDFIELDER, 0.45, 0.25),
        _slot(Position.MIDFIELDER, 0.45, 0.50),
        _slot(Position.MIDFIELDER, 0.45, 0.75),
        _slot(Position.FORWARD, 0.68, 0.50),
    ),
)

# Formaciones por tamano de equipo. Se ira ampliando (11v11, etc.).
DEFAULT_FORMATIONS: dict[int, Formation] = {7: FORMATION_7}


def slot_to_meters(slot: FormationSlot, side: Side, pitch: Pitch) -> Vec2:
    """Ubicacion en metros de un slot para un equipo (espeja al visitante)."""
    if side is Side.HOME:
        x = slot.rel_x * pitch.length
    else:
        x = (1.0 - slot.rel_x) * pitch.length
    y = slot.rel_y * pitch.width
    return Vec2(x, y)


def pick_lineup(club: Club, formation: Formation) -> list[Player]:
    """Elige los titulares: el mejor disponible para la posicion de cada slot."""
    by_position: dict[Position, list[Player]] = {}
    for player in sorted(club.players, key=lambda p: p.overall, reverse=True):
        by_position.setdefault(player.position, []).append(player)

    # Jugadores de campo ordenados por overall (para el fallback).
    outfield = [
        p
        for p in sorted(club.players, key=lambda p: p.overall, reverse=True)
        if p.position is not Position.GOALKEEPER
    ]

    used: set[int] = set()
    lineup: list[Player] = []
    for slot in formation.slots:
        candidates = by_position.get(slot.position, [])
        pick = next((p for p in candidates if id(p) not in used), None)
        if pick is None:
            # No hay de esa posicion: cae al mejor jugador de campo no usado;
            # un arquero suplente solo como ultimo recurso.
            pick = next((p for p in outfield if id(p) not in used), None)
        if pick is None:
            pick = next(p for p in club.players if id(p) not in used)
        used.add(id(pick))
        lineup.append(pick)
    return lineup
