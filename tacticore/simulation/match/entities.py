"""Entidades del partido en tiempo real: jugador y pelota en la cancha.

Son los objetos "vivos" del partido (mutables, su posicion/velocidad cambian en
cada tick). Referencian al `Player` del dominio para leer sus atributos.
"""

from dataclasses import dataclass, field
from enum import Enum

from ...domain.player import Player
from .geometry import Vec2

_ZERO = Vec2(0.0, 0.0)


class Side(Enum):
    """Equipo: local o visitante."""

    HOME = "home"
    AWAY = "away"


class Role(Enum):
    """Rol del jugador en la formacion: define su comportamiento en cancha.

    Mas granular que `Position` (que es la posicion natural del jugador): un
    DEFENDER puede jugar de central (`CENTER_BACK`) o de lateral (`FULLBACK`),
    un FORWARD de extremo (`WINGER`) o de punta (`STRIKER`). El rol decide como
    se mueve (ancho, subir, aguantar la linea), no quien es el jugador.
    """

    GOALKEEPER = "GK"
    CENTER_BACK = "CB"
    FULLBACK = "FB"
    MIDFIELDER = "MID"
    WINGER = "WG"
    STRIKER = "ST"


@dataclass
class MatchPlayer:
    """Un jugador dentro del partido (posicion/velocidad en metros)."""

    player: Player
    team: Side
    position: Vec2
    base_position: Vec2          # ancla de la formacion (para volver a su zona)
    role: Role = Role.MIDFIELDER  # rol en la formacion (comportamiento)
    velocity: Vec2 = _ZERO

    @property
    def name(self) -> str:
        return self.player.display_name

    @property
    def number(self) -> int | None:
        return self.player.shirt_number


@dataclass
class Ball:
    """La pelota (posicion/velocidad en metros)."""

    position: Vec2
    velocity: Vec2 = _ZERO
    owner: MatchPlayer | None = None  # quien la tiene (None si esta suelta)


@dataclass
class Referee:
    """El arbitro: sigue la jugada a distancia. No es jugador ni toca la pelota."""

    position: Vec2
    velocity: Vec2 = _ZERO
