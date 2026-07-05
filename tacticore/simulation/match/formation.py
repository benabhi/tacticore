"""Formaciones: como se ubican los jugadores en la cancha.

Una formacion es una lista de "slots" (posicion + ubicacion relativa). Las
coordenadas relativas son 0..1: `rel_x` va de 0 (arco propio) a 1 (arco rival),
`rel_y` de 0 a 1 a lo ancho. Se mapean a metros y se espejan para el visitante.

El juego es 11v11: mas abajo estan las formaciones mas usadas del futbol
(4-3-3, 4-4-2, 4-2-3-1, 4-1-4-1, 3-5-2, 3-4-3, 5-3-2, 5-4-1). El manager elige una
por partido; `auto_select`/`pick_lineup` la usan para armar el equipo.
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


# El rol (comportamiento en cancha) se deriva de la posicion del slot, asi no hay
# que repetirlo en cada formacion. Se puede override pasando `role` a _slot.
_ROLE_BY_POSITION: dict[Position, Role] = {
    Position.GOALKEEPER: Role.GOALKEEPER,
    Position.CENTER_BACK: Role.CENTER_BACK,
    Position.LEFT_BACK: Role.FULLBACK,
    Position.RIGHT_BACK: Role.FULLBACK,
    Position.DEF_MID: Role.MIDFIELDER,
    Position.CENTER_MID: Role.MIDFIELDER,
    Position.ATT_MID: Role.MIDFIELDER,
    Position.LEFT_MID: Role.WINGER,
    Position.RIGHT_MID: Role.WINGER,
    Position.LEFT_WING: Role.WINGER,
    Position.RIGHT_WING: Role.WINGER,
    Position.STRIKER: Role.STRIKER,
}


def _slot(
    position: Position, rel_x: float, rel_y: float, role: Role | None = None
) -> FormationSlot:
    return FormationSlot(position, rel_x, rel_y, role or _ROLE_BY_POSITION[position])


def _formation(name: str, lines: list) -> Formation:
    """Arma una formacion desde sus lineas. Cada linea es (rel_x, [(pos, rel_y)...]).

    El arquero se agrega solo (todas lo tienen). rel_x: 0 arco propio -> 1 rival;
    rel_y: 0..1 a lo ancho. El rol sale de la posicion (ver _ROLE_BY_POSITION).
    """
    slots = [_slot(Position.GOALKEEPER, 0.05, 0.50)]
    for rel_x, entries in lines:
        for position, rel_y in entries:
            slots.append(_slot(position, rel_x, rel_y))
    return Formation(name, tuple(slots))


# Profundidad (rel_x) tipica de cada linea. El mediocampo va un poco por delante
# de la mitad (0.44) para que los marcadores no queden sobre la linea central.
_X_DEF, _X_DM, _X_MID, _X_AM, _X_ATT, _X_ST1 = 0.19, 0.34, 0.44, 0.58, 0.72, 0.74
# Aperturas (rel_y) tipicas.
_BACK4 = [(Position.RIGHT_BACK, 0.15), (Position.CENTER_BACK, 0.38),
          (Position.CENTER_BACK, 0.62), (Position.LEFT_BACK, 0.85)]
_BACK3 = [(Position.CENTER_BACK, 0.28), (Position.CENTER_BACK, 0.50),
          (Position.CENTER_BACK, 0.72)]
_BACK5 = [(Position.RIGHT_BACK, 0.10), (Position.CENTER_BACK, 0.30),
          (Position.CENTER_BACK, 0.50), (Position.CENTER_BACK, 0.70),
          (Position.LEFT_BACK, 0.90)]

# --- Formaciones 11v11 mas usadas del futbol ---
FORMATION_433 = _formation("4-3-3", [
    (_X_DEF, _BACK4),
    (_X_MID, [(Position.DEF_MID, 0.25), (Position.CENTER_MID, 0.50),
              (Position.ATT_MID, 0.75)]),
    (_X_ATT, [(Position.RIGHT_WING, 0.20), (Position.STRIKER, 0.50),
              (Position.LEFT_WING, 0.80)]),
])
FORMATION_442 = _formation("4-4-2", [
    (_X_DEF, _BACK4),
    (_X_MID, [(Position.RIGHT_MID, 0.15), (Position.CENTER_MID, 0.40),
              (Position.CENTER_MID, 0.60), (Position.LEFT_MID, 0.85)]),
    (_X_ATT, [(Position.STRIKER, 0.38), (Position.STRIKER, 0.62)]),
])
FORMATION_4231 = _formation("4-2-3-1", [
    (_X_DEF, _BACK4),
    (_X_DM, [(Position.DEF_MID, 0.38), (Position.DEF_MID, 0.62)]),
    (_X_AM, [(Position.RIGHT_WING, 0.20), (Position.ATT_MID, 0.50),
             (Position.LEFT_WING, 0.80)]),
    (_X_ST1, [(Position.STRIKER, 0.50)]),
])
FORMATION_4141 = _formation("4-1-4-1", [
    (_X_DEF, _BACK4),
    (_X_DM, [(Position.DEF_MID, 0.50)]),
    (_X_MID, [(Position.RIGHT_MID, 0.15), (Position.CENTER_MID, 0.40),
              (Position.CENTER_MID, 0.60), (Position.LEFT_MID, 0.85)]),
    (_X_ST1, [(Position.STRIKER, 0.50)]),
])
FORMATION_352 = _formation("3-5-2", [
    (_X_DEF, _BACK3),
    (_X_MID, [(Position.RIGHT_MID, 0.10), (Position.CENTER_MID, 0.32),
              (Position.DEF_MID, 0.50), (Position.CENTER_MID, 0.68),
              (Position.LEFT_MID, 0.90)]),
    (_X_ATT, [(Position.STRIKER, 0.38), (Position.STRIKER, 0.62)]),
])
FORMATION_343 = _formation("3-4-3", [
    (_X_DEF, _BACK3),
    (_X_MID, [(Position.RIGHT_MID, 0.12), (Position.CENTER_MID, 0.38),
              (Position.CENTER_MID, 0.62), (Position.LEFT_MID, 0.88)]),
    (_X_ATT, [(Position.RIGHT_WING, 0.20), (Position.STRIKER, 0.50),
              (Position.LEFT_WING, 0.80)]),
])
FORMATION_532 = _formation("5-3-2", [
    (_X_DEF, _BACK5),
    (_X_MID, [(Position.DEF_MID, 0.25), (Position.CENTER_MID, 0.50),
              (Position.ATT_MID, 0.75)]),
    (_X_ATT, [(Position.STRIKER, 0.38), (Position.STRIKER, 0.62)]),
])
FORMATION_541 = _formation("5-4-1", [
    (_X_DEF, _BACK5),
    (_X_MID, [(Position.RIGHT_MID, 0.15), (Position.CENTER_MID, 0.40),
              (Position.CENTER_MID, 0.60), (Position.LEFT_MID, 0.85)]),
    (_X_ST1, [(Position.STRIKER, 0.50)]),
])

# Alias de compatibilidad (el motor y los tests referencian estos nombres).
FORMATION_11 = FORMATION_433
FORMATION_11_442 = FORMATION_442

# Formaciones 11v11 disponibles, en orden de rotacion (el manager elige una).
FORMATIONS_11: tuple[Formation, ...] = (
    FORMATION_433, FORMATION_442, FORMATION_4231, FORMATION_4141,
    FORMATION_352, FORMATION_343, FORMATION_532, FORMATION_541,
)
FORMATIONS = FORMATIONS_11  # alias legible para la UI

# Formaciones por tamano de equipo. El juego es 11v11.
DEFAULT_FORMATIONS: dict[int, Formation] = {11: FORMATION_11}

# Formaciones por nombre (para resolver el nombre guardado en la tactica).
FORMATIONS_BY_NAME: dict[str, Formation] = {f.name: f for f in FORMATIONS_11}


def get_formation(name: str) -> Formation:
    """Devuelve la formacion por nombre (4-3-3 por defecto si no existe)."""
    return FORMATIONS_BY_NAME.get(name, FORMATION_11)


def auto_select(
    club: Club, formation: Formation, bench_size: int = 5,
    available_only: bool = False,
) -> tuple[list[Player], list[Player]]:
    """Alineacion automatica: 11 titulares (pick_lineup) + banco con los mejores.

    Los titulares se eligen por posicion preferida y habilidad (ver pick_lineup);
    el banco son los mejores del resto del plantel (por overall), hasta bench_size.
    Con `available_only`, se saltean lesionados/suspendidos (banco incluido).
    """
    lineup = pick_lineup(club, formation, available_only=available_only)
    used = {id(p) for p in lineup}
    pool = [p for p in club.players if not available_only or p.is_available]
    rest = [p for p in sorted(pool, key=lambda p: p.overall, reverse=True)
            if id(p) not in used]
    return lineup, rest[:bench_size]


def slot_to_meters(slot: FormationSlot, side: Side, pitch: Pitch) -> Vec2:
    """Ubicacion en metros de un slot para un equipo (espeja al visitante)."""
    if side is Side.HOME:
        x = slot.rel_x * pitch.length
    else:
        x = (1.0 - slot.rel_x) * pitch.length
    y = slot.rel_y * pitch.width
    return Vec2(x, y)


def pick_lineup(
    club: Club, formation: Formation, available_only: bool = False
) -> list[Player]:
    """Elige los titulares: el mejor disponible para cada slot.

    Prioridad por slot: 1) jugador de esa posicion exacta; 2) de la misma linea
    (un MCO falta -> otro mediocampista); 3) el mejor de campo libre; 4) lo que
    quede (arquero suplente solo como ultimo recurso). Todo por overall.

    Con `available_only` se excluyen lesionados/suspendidos; si no alcanzan para
    llenar la formacion, se completa con los no disponibles (para no dejar huecos).
    """
    players = club.players
    if available_only:
        available = [p for p in players if p.is_available]
        # Solo se filtra si quedan al menos los 11 (si no, se juega con lo que hay).
        if len(available) >= formation.size:
            players = available
    ranked = sorted(players, key=lambda p: p.overall, reverse=True)
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
