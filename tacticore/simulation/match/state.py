"""Estado del partido y armado del estado inicial (saque del medio).

`MatchState` es el contenedor de todo lo que pasa en un partido: jugadores de
ambos equipos, pelota, marcador, reloj y fase. `kickoff_state` arma el estado
inicial a partir de dos clubes y una formacion.
"""

from dataclasses import dataclass, field
from enum import Enum

from ...domain.club import Club
from .entities import Ball, MatchPlayer, Referee, Side
from .field import Pitch
from .formation import DEFAULT_FORMATIONS, Formation, pick_lineup, slot_to_meters
from .geometry import Vec2


class MatchPhase(Enum):
    """Fase del partido."""

    KICKOFF = "kickoff"
    PLAYING = "playing"
    GOAL = "goal"
    FINISHED = "finished"


@dataclass
class MatchState:
    """Todo el estado de un partido en curso."""

    pitch: Pitch
    home: list[MatchPlayer]
    away: list[MatchPlayer]
    ball: Ball
    referee: Referee = field(default_factory=lambda: Referee(Vec2(0.0, 0.0)))
    score_home: int = 0
    score_away: int = 0
    clock: float = 0.0  # segundos de tiempo de juego transcurridos
    phase: MatchPhase = MatchPhase.KICKOFF

    def all_players(self) -> list[MatchPlayer]:
        """Todos los jugadores en cancha (local + visitante)."""
        return [*self.home, *self.away]

    def team(self, side: Side) -> list[MatchPlayer]:
        """Los jugadores de un equipo."""
        return self.home if side is Side.HOME else self.away


def _place_team(club: Club, side: Side, formation: Formation, pitch: Pitch) -> list[MatchPlayer]:
    """Ubica a los titulares de un club en sus posiciones de formacion."""
    players = pick_lineup(club, formation)
    placed = []
    for slot, player in zip(formation.slots, players):
        pos = slot_to_meters(slot, side, pitch)
        placed.append(MatchPlayer(player=player, team=side, position=pos, base_position=pos))
    return placed


def kickoff_state(
    home_club: Club,
    away_club: Club,
    pitch: Pitch | None = None,
    formation: Formation | None = None,
) -> MatchState:
    """Arma el estado inicial: equipos ubicados y pelota en el centro.

    Por defecto usa la formacion 7v7 de prueba; se le puede pasar otra.
    """
    pitch = pitch or Pitch()
    formation = formation or DEFAULT_FORMATIONS[7]
    home = _place_team(home_club, Side.HOME, formation, pitch)
    away = _place_team(away_club, Side.AWAY, formation, pitch)
    ball = Ball(position=pitch.center)
    referee = Referee(position=pitch.center)
    return MatchState(pitch=pitch, home=home, away=away, ball=ball, referee=referee)
