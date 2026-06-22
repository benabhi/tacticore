"""Enumeraciones del dominio (posiciones, pie, especialidades, estado, etc.)."""

from enum import Enum


class Position(Enum):
    """Posicion natural de un jugador en el campo."""

    GOALKEEPER = "GK"
    DEFENDER = "DEF"
    MIDFIELDER = "MID"
    FORWARD = "FWD"


class Foot(Enum):
    """Pie habil de un jugador."""

    LEFT = "L"
    RIGHT = "R"
    BOTH = "B"


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
