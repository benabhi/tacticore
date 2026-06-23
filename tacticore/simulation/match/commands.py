"""Comandos del manager: ordenes selladas con el tick en que se aplican.

Un partido reproducible = `seed` + esta lista de comandos. El motor lee los
comandos de su cola al inicio de cada tick; da igual si los puso la UI en vivo o
si vienen de un partido grabado (replay): el motor no nota la diferencia, asi
que misma seed + mismos comandos -> mismo partido. Ver docs/DESIGN.md seccion 13.

Para sumar una orden nueva (sustitucion, cambio de tactica, presion, ...) se
agrega una dataclass que herede de `Command` y defina su `apply`. Nada mas del
motor necesita cambiar.
"""

from dataclasses import dataclass

from .entities import Side
from .geometry import Vec2
from .state import MatchState


@dataclass(frozen=True)
class Command:
    """Orden base. `tick` es el paso de simulacion en que el motor la aplica."""

    tick: int

    def apply(self, state: MatchState) -> None:
        """Aplica el efecto sobre el estado del partido."""
        raise NotImplementedError


@dataclass(frozen=True)
class SetPlayerZone(Command):
    """Mueve el ancla de formacion de un jugador (cambiarle la zona).

    `player_index` indexa la lista del equipo en cancha. El jugador volvera a
    `zone` cuando no este persiguiendo la pelota.
    """

    side: Side
    player_index: int
    zone: Vec2

    def apply(self, state: MatchState) -> None:
        state.team(self.side)[self.player_index].base_position = self.zone
