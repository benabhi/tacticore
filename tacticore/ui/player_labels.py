"""Etiquetas en espanol para mostrar datos de jugadores (capa UI).

Traduce enums y nombres de atributos a texto en pantalla (ASCII, directiva 2).
Lo usan la tabla de plantilla y la ficha del jugador.
"""

from ..domain.enums import Foot, Morale, Position, Specialty
from ..domain.player import MENTAL_ATTRS, PHYSICAL_ATTRS, TECHNICAL_ATTRS

# Posicion: nombre completo en espanol (la sigla es Position.value, ej. "LI").
POSITION_LABEL = {
    Position.GOALKEEPER: "Arquero",
    Position.CENTER_BACK: "Defensor central",
    Position.LEFT_BACK: "Lateral izquierdo",
    Position.RIGHT_BACK: "Lateral derecho",
    Position.DEF_MID: "Mediocampista defensivo",
    Position.CENTER_MID: "Mediocampista central",
    Position.ATT_MID: "Mediocampista ofensivo",
    Position.LEFT_MID: "Volante izquierdo",
    Position.RIGHT_MID: "Volante derecho",
    Position.LEFT_WING: "Extremo izquierdo",
    Position.RIGHT_WING: "Extremo derecho",
    Position.STRIKER: "Delantero centro",
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

# Rasgos de personalidad 1-5 (de peor a mejor), como la moral.
LEADERSHIP_LABEL = {
    1: "Pasivo", 2: "Reservado", 3: "Normal", 4: "Referente", 5: "Lider nato",
}
CHARACTER_LABEL = {
    1: "Irrespetuoso", 2: "Rebelde", 3: "Normal", 4: "Profesional", 5: "Ejemplar",
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

# Codigo corto de cada especialidad (para la tabla de plantilla).
SPECIALTY_SHORT = {
    Specialty.HEADER: "CAB",
    Specialty.POWERFUL: "PWR",
    Specialty.QUICK: "VEL",
    Specialty.TECHNICAL: "TEC",
    Specialty.UNPREDICTABLE: "IMP",
    Specialty.POACHER: "CAZ",
    Specialty.PLAYMAKER: "CER",
    Specialty.DEAD_BALL: "CAN",
    Specialty.ROCK: "MUR",
    Specialty.CAT: "FEL",
    Specialty.IRON: "HIE",
    Specialty.LEADER: "LID",
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

# Abreviatura de 3 letras de cada atributo (para vistas compactas, ej. el panel
# de tactica). El nombre completo esta en ATTR_LABEL.
ATTR_SHORT = {
    "speed": "VEL",
    "stamina": "RES",
    "strength": "FUE",
    "agility": "AGI",
    "aerial": "AER",
    "passing": "PAS",
    "shooting": "REM",
    "dribbling": "REG",
    "tackling": "ENT",
    "crossing": "CEN",
    "vision": "VIS",
    "positioning": "POS",
    "anticipation": "ANT",
    "composure": "TEM",
    "work_rate": "SAC",
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
