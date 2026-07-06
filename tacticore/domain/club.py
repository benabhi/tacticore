"""Entidad Club."""

from dataclasses import dataclass, field

from .coach import Coach
from .employee import Employee
from .enums import LeagueTier
from .facility import Construction
from .manager import Manager
from .movement import Movement
from .player import Player
from .sponsor import SponsorContract
from .stadium import Stadium


@dataclass
class Club:
    """Un club: identidad, finanzas, estadio, hinchada, manager, DT y plantilla."""

    name: str
    short_name: str
    country_code: str   # pais al que pertenece (ej. "ARG")
    tier: LeagueTier    # nivel de liga en el que juega
    stadium: Stadium
    capital: int = 0    # dinero inicial
    members: int = 0    # cantidad de asociados / socios
    fans_name: str = ""             # nombre de la hinchada (ej. "La Furia Roja")
    manager: Manager | None = None  # quien dirige la institucion (el jugador o un IA)
    players: list[Player] = field(default_factory=list)
    coach: Coach | None = None      # director tecnico (dirige al equipo)
    employees: list[Employee] = field(default_factory=list)  # cuerpo de trabajo (medico, etc.)
    sponsors: list[SponsorContract] = field(default_factory=list)  # contratos de patrocinio (cupos por tier)
    plots: int = 0                  # parcelas de terreno (limitan cuanto se construye)
    facilities: dict[str, int] = field(default_factory=dict)  # id edificio -> nivel
    stands_built: int = 0           # gradas de estadio construidas (ocupan parcela)
    constructions: list[Construction] = field(default_factory=list)  # obras en curso
    formation_training: dict[str, float] = field(default_factory=dict)  # formacion -> nivel 1-100
    movements: list[Movement] = field(default_factory=list)  # libro de caja (solo el club del jugador)

    @property
    def squad_size(self) -> int:
        """Cantidad de jugadores en la plantilla."""
        return len(self.players)

    @property
    def overall(self) -> int:
        """Media de overall de la plantilla (0 si no hay jugadores)."""
        if not self.players:
            return 0
        return round(sum(p.overall for p in self.players) / len(self.players))
