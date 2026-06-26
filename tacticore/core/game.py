"""Estado raiz del juego.

`GameState` es el contenedor de todo lo que define una partida en curso:
semilla, calendario, el mundo (paises -> ligas -> clubes -> jugadores), cual es
el club del jugador y el nombre del presidente humano. La UI lee de aca y las
acciones del jugador lo modifican (a traves de la simulacion), nunca al reves.
Se serializa entero al guardar (ver persistence/savegame.py).
"""

from dataclasses import dataclass, field
from datetime import date

from ..domain.club import Club
from ..domain.country import Country
from ..domain.enums import LeagueTier
from .calendar import GameCalendar


@dataclass
class GameState:
    """Contenedor raiz del estado de una partida."""

    seed: int
    calendar: GameCalendar
    countries: list[Country] = field(default_factory=list)
    player_club: Club | None = None      # el club que dirige el jugador
    president_name: str = ""              # nombre del presidente humano (el jugador)

    @classmethod
    def new(cls, seed: int, start_date: date, countries: list[Country] | None = None) -> "GameState":
        """Crea un estado de juego con el mundo ya generado (o vacio)."""
        return cls(
            seed=seed,
            calendar=GameCalendar(current_date=start_date),
            countries=countries or [],
        )

    def install_player_club(self, club: Club) -> None:
        """Mete el club del jugador en la liga E de su pais (reemplaza un club IA).

        La liga sigue teniendo la misma cantidad de clubes. Deja `player_club`
        apuntando al club instalado.
        """
        for country in self.countries:
            if country.code != club.country_code:
                continue
            for league in country.leagues:
                if league.tier is LeagueTier.E:
                    league.clubs[0] = club
                    self.player_club = club
                    return
        raise ValueError(f"No hay liga E para el pais {club.country_code!r} en el mundo.")
