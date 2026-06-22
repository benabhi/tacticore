"""Entidad Club."""

from dataclasses import dataclass, field

from .enums import LeagueTier
from .player import Player
from .stadium import Stadium


@dataclass
class Club:
    """Un club: identidad, finanzas basicas, estadio y plantilla."""

    name: str
    short_name: str
    country_code: str   # pais al que pertenece (ej. "ARG")
    tier: LeagueTier    # nivel de liga en el que juega
    stadium: Stadium
    capital: int = 0    # dinero inicial
    members: int = 0    # cantidad de asociados / socios
    players: list[Player] = field(default_factory=list)

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
