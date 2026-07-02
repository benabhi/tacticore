"""Enumeraciones del dominio (posiciones, pie, especialidades, estado, etc.)."""

from enum import Enum


class Position(Enum):
    """Posicion natural (preferida) de un jugador, al estandar del futbol.

    El nombre del miembro va en ingles (directiva 4); el valor es la sigla en
    espanol que se muestra en pantalla (directiva 2/4). La agrupacion por linea
    (arco/defensa/medio/ataque) y los atributos prioritarios de cada posicion
    viven en `domain/positions.py`. El comportamiento en cancha lo define `Role`
    (ver simulation/match/entities.py), no esta posicion.
    """

    GOALKEEPER = "ARQ"   # Arquero
    CENTER_BACK = "DFC"  # Defensor central
    LEFT_BACK = "LI"     # Lateral izquierdo
    RIGHT_BACK = "LD"    # Lateral derecho
    DEF_MID = "MCD"      # Mediocampista central defensivo
    CENTER_MID = "MC"    # Mediocampista central
    ATT_MID = "MCO"      # Mediocampista central ofensivo (enganche)
    LEFT_MID = "MI"      # Volante izquierdo
    RIGHT_MID = "MD"     # Volante derecho
    LEFT_WING = "EI"     # Extremo izquierdo
    RIGHT_WING = "ED"    # Extremo derecho
    STRIKER = "DC"       # Delantero centro


class Foot(Enum):
    """Pie habil de un jugador."""

    LEFT = "L"
    RIGHT = "R"
    BOTH = "B"


class LeagueTier(Enum):
    """Nivel de una liga dentro de un pais (A es la mejor, E la mas baja).

    Los managers nuevos arrancan en la liga E. El orden de definicion (A->E)
    es el orden de calidad.
    """

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"


class Specialty(Enum):
    """Especialidades raras al estilo Hattrick (un jugador tiene 0 o 1).

    Cada una modifica la simulacion mas alla de los numeros (ver simulation/).
    """

    HEADER = "header"                # Cabeceador: bonus aereo
    POWERFUL = "powerful"            # Potente: domina duelos / rinde cansado
    QUICK = "quick"                  # Veloz: arranque explosivo
    TECHNICAL = "technical"          # Tecnico: regate y control fino
    UNPREDICTABLE = "unpredictable"  # Impredecible: crea (y falla) de la nada
    POACHER = "poacher"              # Cazagoles: oportunista en el area
    PLAYMAKER = "playmaker"          # Cerebro: organiza y mejora companeros
    DEAD_BALL = "dead_ball"          # Canonero: tiros libres y penales
    ROCK = "rock"                    # Muralla: defensor que aguanta todo
    CAT = "cat"                      # Felino: arquero con reflejos extra
    IRON = "iron"                    # De Hierro: casi nunca se lesiona
    LEADER = "leader"                # Lider: sube la moral del equipo


class MatchKind(Enum):
    """Tipo de partido (define la competicion). El valor es la etiqueta en pantalla."""

    LEAGUE = "Liga"
    FRIENDLY = "Amistoso"
    CUP = "Copa"


class Mentality(Enum):
    """Mentalidad del equipo para un partido. El valor es la etiqueta en pantalla."""

    DEFENSIVE = "Defensiva"
    NEUTRAL = "Neutral"
    OFFENSIVE = "Ofensiva"


class TeamTactic(Enum):
    """Tactica general del equipo (al estilo Hattrick). Valor = etiqueta en pantalla."""

    NORMAL = "Normal"
    COUNTER = "Contraataque"
    WINGS = "Ataque por bandas"
    THROUGH_MIDDLE = "Juego por el medio"
    LONG_BALL = "Pelotazo"
    PRESSING = "Presion alta"


class Marking(Enum):
    """Esquema de marcaje por defecto del equipo. Valor = etiqueta en pantalla.

    Es el default del equipo para el partido; mas adelante el motor podra sesgar
    la defensa segun este valor (zonal = cuidar zona; personal = hombre a hombre).
    Complementa la marca individual por jugador (comando en-vivo `SetMarking`).
    """

    ZONAL = "Zonal"
    PERSONAL = "Personal"


class Morale(Enum):
    """Estado animico del jugador (de peor a mejor)."""

    DEVASTATED = 1
    UNHAPPY = 2
    NEUTRAL = 3
    CONTENT = 4
    FIRED_UP = 5


class InjuryType(Enum):
    """Tipo de lesion."""

    KNOCK = "knock"          # golpe leve
    MUSCLE = "muscle"        # muscular
    HAMSTRING = "hamstring"  # isquiotibial
    ANKLE = "ankle"          # tobillo
    KNEE = "knee"            # rodilla
    HEAD = "head"            # conmocion
    FRACTURE = "fracture"    # fractura


class InjurySeverity(Enum):
    """Gravedad de una lesion (de menor a mayor)."""

    MINOR = 1     # leve
    MODERATE = 2  # media
    SEVERE = 3    # grave
