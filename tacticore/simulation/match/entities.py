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


@dataclass
class MatchPlayer:
    """Un jugador dentro del partido (posicion/velocidad en metros)."""

    player: Player
    team: Side
    position: Vec2
    base_position: Vec2          # ancla de la formacion (para volver a su zona)
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
