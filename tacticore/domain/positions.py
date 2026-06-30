"""Metadata de las posiciones: linea (arco/defensa/medio/ataque) y atributos
prioritarios de cada una.

Es la fuente unica de verdad que comparten el generador (para sesgar los
atributos al generar un jugador) y la UI (para resaltar, en la ficha, los
atributos clave de la posicion). Los atributos referencian los campos de
`domain/player.py`.
"""

from enum import Enum

from .enums import Position


class Line(Enum):
    """Linea de la cancha a la que pertenece una posicion."""

    GOALKEEPER = "GK"
    DEFENSE = "DEF"
    MIDFIELD = "MID"
    ATTACK = "FWD"


# Posiciones agrupadas por linea (el orden es de defensa a ataque).
GOALKEEPERS = (Position.GOALKEEPER,)
DEFENDERS = (Position.CENTER_BACK, Position.LEFT_BACK, Position.RIGHT_BACK)
MIDFIELDERS = (
    Position.DEF_MID, Position.CENTER_MID, Position.ATT_MID,
    Position.LEFT_MID, Position.RIGHT_MID,
)
ATTACKERS = (Position.LEFT_WING, Position.RIGHT_WING, Position.STRIKER)

_LINE_OF: dict[Position, Line] = (
    {p: Line.GOALKEEPER for p in GOALKEEPERS}
    | {p: Line.DEFENSE for p in DEFENDERS}
    | {p: Line.MIDFIELD for p in MIDFIELDERS}
    | {p: Line.ATTACK for p in ATTACKERS}
)


def line_of(position: Position) -> Line:
    """Linea (arco/defensa/medio/ataque) de una posicion."""
    return _LINE_OF[position]


def is_goalkeeper(position: Position) -> bool:
    """Si la posicion es la de arquero."""
    return position is Position.GOALKEEPER


# Atributos clave de cada posicion, ordenados de mas a menos importante. Cada
# atributo es un campo de `Player`. Entre las 12 posiciones se usan los 15
# atributos, asi que todos tienen peso en alguna posicion.
POSITION_PRIORITIES: dict[Position, tuple[str, ...]] = {
    Position.GOALKEEPER: ("agility", "positioning", "composure", "anticipation", "aerial"),
    Position.CENTER_BACK: ("tackling", "positioning", "aerial", "strength", "anticipation"),
    Position.LEFT_BACK: ("speed", "stamina", "tackling", "crossing", "work_rate"),
    Position.RIGHT_BACK: ("speed", "stamina", "tackling", "crossing", "work_rate"),
    Position.DEF_MID: ("tackling", "positioning", "anticipation", "work_rate", "strength"),
    Position.CENTER_MID: ("passing", "vision", "stamina", "work_rate", "composure"),
    Position.ATT_MID: ("vision", "passing", "dribbling", "shooting", "composure"),
    Position.LEFT_MID: ("work_rate", "crossing", "speed", "stamina", "passing"),
    Position.RIGHT_MID: ("work_rate", "crossing", "speed", "stamina", "passing"),
    Position.LEFT_WING: ("speed", "dribbling", "crossing", "agility", "shooting"),
    Position.RIGHT_WING: ("speed", "dribbling", "crossing", "agility", "shooting"),
    Position.STRIKER: ("shooting", "aerial", "dribbling", "composure", "speed"),
}
