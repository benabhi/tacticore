"""Estado raiz del juego.

`GameState` es el contenedor de todo lo que define una partida en curso:
calendario, ligas/clubes, semilla, etc. La UI lee de aca y las acciones del
jugador lo modifican (a traves de la simulacion), nunca al reves.
"""

from dataclasses import dataclass, field
from datetime import date

from ..domain.league import League
from .calendar import GameCalendar


@dataclass
class GameState:
    """Contenedor raiz del estado de una partida."""

    seed: int
    calendar: GameCalendar
    leagues: list[League] = field(default_factory=list)

    @classmethod
    def new(cls, seed: int, start_date: date) -> "GameState":
        """Crea un estado de juego vacio listo para poblar con generadores."""
        return cls(seed=seed, calendar=GameCalendar(current_date=start_date))
