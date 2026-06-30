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
from ...domain.positions import is_goalkeeper, line_of
from .entities import Role, Side
from .field import Pitch
from .geometry import Vec2


@dataclass(frozen=True)
class FormationSlot:
    """Un puesto de la formacion: posicion natural + ubicacion + rol.

    `position` decide que jugador del plantel lo ocupa (al armar el 11);
    `role` decide como se comporta en la cancha (ancho, subir, marcar, etc.).
    """

    position: Position
    rel_x: float  # 0 = arco propio, 1 = arco rival
    rel_y: float  # 0..1 a lo ancho
    role: Role


@dataclass(frozen=True)
class Formation:
    """Una formacion (su cantidad de slots define el tamano del equipo)."""

    name: str
    slots: tuple[FormationSlot, ...]

    @property
    def size(self) -> int:
        return len(self.slots)


def _slot(position: Position, rel_x: float, rel_y: float, role: Role) -> FormationSlot:
    return FormationSlot(position, rel_x, rel_y, role)

# Formacion 7v7 (1-2-3-1): config de prueba inicial del motor.
FORMATION_7 = Formation(
    "1-2-3-1",
    (
        _slot(Position.GOALKEEPER, 0.05, 0.50, Role.GOALKEEPER),
        _slot(Position.CENTER_BACK, 0.22, 0.30, Role.CENTER_BACK),
        _slot(Position.CENTER_BACK, 0.22, 0.70, Role.CENTER_BACK),
        _slot(Position.RIGHT_MID, 0.45, 0.25, Role.WINGER),
        _slot(Position.CENTER_MID, 0.45, 0.50, Role.MIDFIELDER),
        _slot(Position.LEFT_MID, 0.45, 0.75, Role.WINGER),
        _slot(Position.STRIKER, 0.68, 0.50, Role.STRIKER),
    ),
)

# Formacion 11v11 (4-3-3): la estandar del juego.
# Defensa: 2 laterales (anchos) + 2 centrales. Ataque: 2 extremos + 1 punta.
FORMATION_11 = Formation(
    "4-3-3",
    (
        _slot(Position.GOALKEEPER, 0.05, 0.50, Role.GOALKEEPER),
        _slot(Position.RIGHT_BACK, 0.20, 0.15, Role.FULLBACK),
        _slot(Position.CENTER_BACK, 0.18, 0.38, Role.CENTER_BACK),
        _slot(Position.CENTER_BACK, 0.18, 0.62, Role.CENTER_BACK),
        _slot(Position.LEFT_BACK, 0.20, 0.85, Role.FULLBACK),
        _slot(Position.DEF_MID, 0.45, 0.30, Role.MIDFIELDER),
        _slot(Position.CENTER_MID, 0.42, 0.50, Role.MIDFIELDER),
        _slot(Position.ATT_MID, 0.45, 0.70, Role.MIDFIELDER),
        _slot(Position.RIGHT_WING, 0.72, 0.18, Role.WINGER),
        _slot(Position.STRIKER, 0.70, 0.50, Role.STRIKER),
        _slot(Position.LEFT_WING, 0.72, 0.82, Role.WINGER),
    ),
)

# Formacion 11v11 (4-4-2): 2 laterales + 2 centrales, 2 extremos + 2 volantes,
# 2 puntas.
FORMATION_11_442 = Formation(
    "4-4-2",
    (
        _slot(Position.GOALKEEPER, 0.05, 0.50, Role.GOALKEEPER),
        _slot(Position.RIGHT_BACK, 0.20, 0.15, Role.FULLBACK),
        _slot(Position.CENTER_BACK, 0.18, 0.40, Role.CENTER_BACK),
        _slot(Position.CENTER_BACK, 0.18, 0.60, Role.CENTER_BACK),
        _slot(Position.LEFT_BACK, 0.20, 0.85, Role.FULLBACK),
        _slot(Position.RIGHT_MID, 0.48, 0.16, Role.WINGER),
        _slot(Position.CENTER_MID, 0.45, 0.40, Role.MIDFIELDER),
        _slot(Position.CENTER_MID, 0.45, 0.60, Role.MIDFIELDER),
        _slot(Position.LEFT_MID, 0.48, 0.84, Role.WINGER),
        _slot(Position.STRIKER, 0.70, 0.40, Role.STRIKER),
        _slot(Position.STRIKER, 0.70, 0.60, Role.STRIKER),
    ),
)

# Formaciones 11v11 disponibles (el manager elegira una antes del partido).
FORMATIONS_11: tuple[Formation, ...] = (FORMATION_11, FORMATION_11_442)

# Formaciones por tamano de equipo. El juego usa 11v11; 7v7 queda para pruebas.
DEFAULT_FORMATIONS: dict[int, Formation] = {7: FORMATION_7, 11: FORMATION_11}


def slot_to_meters(slot: FormationSlot, side: Side, pitch: Pitch) -> Vec2:
    """Ubicacion en metros de un slot para un equipo (espeja al visitante)."""
    if side is Side.HOME:
        x = slot.rel_x * pitch.length
    else:
        x = (1.0 - slot.rel_x) * pitch.length
    y = slot.rel_y * pitch.width
    return Vec2(x, y)


def pick_lineup(club: Club, formation: Formation) -> list[Player]:
    """Elige los titulares: el mejor disponible para cada slot.

    Prioridad por slot: 1) jugador de esa posicion exacta; 2) de la misma linea
    (un MCO falta -> otro mediocampista); 3) el mejor de campo libre; 4) lo que
    quede (arquero suplente solo como ultimo recurso). Todo por overall.
    """
    ranked = sorted(club.players, key=lambda p: p.overall, reverse=True)
    by_position: dict[Position, list[Player]] = {}
    by_line: dict[object, list[Player]] = {}
    for player in ranked:
        by_position.setdefault(player.position, []).append(player)
        by_line.setdefault(line_of(player.position), []).append(player)
    outfield = [p for p in ranked if not is_goalkeeper(p.position)]

    used: set[int] = set()
    lineup: list[Player] = []
    for slot in formation.slots:
        pools = (
            by_position.get(slot.position, []),
            by_line.get(line_of(slot.position), []),
            outfield,
            club.players,
        )
        pick = None
        for pool in pools:
            pick = next((p for p in pool if id(p) not in used), None)
            if pick is not None:
                break
        used.add(id(pick))
        lineup.append(pick)
    return lineup
