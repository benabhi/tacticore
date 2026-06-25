"""Estado del partido y armado del estado inicial (saque del medio).

`MatchState` es el contenedor de todo lo que pasa en un partido: jugadores de
ambos equipos, pelota, marcador, reloj y fase. `kickoff_state` arma el estado
inicial a partir de dos clubes y una formacion.
"""

from dataclasses import dataclass, field
from enum import Enum

from ...domain.club import Club
from .entities import Ball, MatchPlayer, Referee, Side
from .events import MatchEvent
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
    last_touch: Side | None = None  # equipo que toco la pelota por ultima vez
    last_event: str | None = None   # ultimo evento (para el HUD): Gol, Lateral, ...
    log: list[MatchEvent] = field(default_factory=list)  # relato estructurado

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
        placed.append(
            MatchPlayer(
                player=player, team=side, position=pos, base_position=pos, role=slot.role
            )
        )
    return placed


def kickoff_state(
    home_club: Club,
    away_club: Club,
    pitch: Pitch | None = None,
    formation: Formation | None = None,
    home_formation: Formation | None = None,
    away_formation: Formation | None = None,
) -> MatchState:
    """Arma el estado inicial: equipos ubicados y pelota en el centro.

    `formation` es el default para ambos; `home_formation`/`away_formation`
    permiten que cada equipo juegue con una formacion distinta.
    """
    pitch = pitch or Pitch()
    default = formation or DEFAULT_FORMATIONS[11]
    home = _place_team(home_club, Side.HOME, home_formation or default, pitch)
    away = _place_team(away_club, Side.AWAY, away_formation or default, pitch)
    ball = Ball(position=pitch.center)
    # El arbitro arranca al costado del centro (no encima de la pelota/pasador).
    referee = Referee(position=pitch.center + Vec2(0.0, 9.0))
    return MatchState(pitch=pitch, home=home, away=away, ball=ball, referee=referee)
