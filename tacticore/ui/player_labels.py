"""Etiquetas en espanol para mostrar datos de jugadores (capa UI).

Traduce enums y nombres de atributos a texto en pantalla (ASCII, directiva 2).
Lo usan la tabla de plantilla y la ficha del jugador.
"""

from ..domain.enums import Foot, Morale, Position, Specialty
from ..domain.player import MENTAL_ATTRS, PHYSICAL_ATTRS, TECHNICAL_ATTRS

# Posicion: nombre completo y sigla corta (para la tabla).
POSITION_LABEL = {
    Position.GOALKEEPER: "Arquero",
    Position.DEFENDER: "Defensor",
    Position.MIDFIELDER: "Mediocampista",
    Position.FORWARD: "Delantero",
}
POSITION_SHORT = {
    Position.GOALKEEPER: "ARQ",
    Position.DEFENDER: "DEF",
    Position.MIDFIELDER: "MED",
    Position.FORWARD: "DEL",
}

FOOT_LABEL = {Foot.LEFT: "Izquierdo", Foot.RIGHT: "Derecho", Foot.BOTH: "Ambidiestro"}
FOOT_SHORT = {Foot.LEFT: "Izq", Foot.RIGHT: "Der", Foot.BOTH: "Amb"}

MORALE_LABEL = {
    Morale.DEVASTATED: "Devastado",
    Morale.UNHAPPY: "Disconforme",
    Morale.NEUTRAL: "Neutral",
    Morale.CONTENT: "Contento",
    Morale.FIRED_UP: "Encendido",
}

SPECIALTY_LABEL = {
    Specialty.HEADER: "Cabeceador",
    Specialty.POWERFUL: "Potente",
    Specialty.QUICK: "Veloz",
    Specialty.TECHNICAL: "Tecnico",
    Specialty.UNPREDICTABLE: "Impredecible",
    Specialty.POACHER: "Cazagoles",
    Specialty.PLAYMAKER: "Cerebro",
    Specialty.DEAD_BALL: "Canonero",
    Specialty.ROCK: "Muralla",
    Specialty.CAT: "Felino",
    Specialty.IRON: "De Hierro",
    Specialty.LEADER: "Lider",
}

# Nombre de cada atributo en pantalla.
ATTR_LABEL = {
    "speed": "Velocidad",
    "stamina": "Resistencia",
    "strength": "Fuerza",
    "agility": "Agilidad",
    "aerial": "Juego aereo",
    "passing": "Pase",
    "shooting": "Remate",
    "dribbling": "Regate",
    "tackling": "Entrada",
    "crossing": "Centro",
    "vision": "Vision",
    "positioning": "Posicion",
    "anticipation": "Anticipacion",
    "composure": "Temple",
    "work_rate": "Sacrificio",
}

# Grupos de atributos (titulo en pantalla + tupla de atributos del dominio).
ATTR_GROUPS = [
    ("FISICOS", PHYSICAL_ATTRS),
    ("TECNICOS", TECHNICAL_ATTRS),
    ("MENTALES", MENTAL_ATTRS),
]


def specialty_label(specialty: Specialty | None) -> str:
    """Nombre de la especialidad, o 'Ninguna'."""
    return SPECIALTY_LABEL[specialty] if specialty else "Ninguna"
