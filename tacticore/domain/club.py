"""Entidad Club."""

from dataclasses import dataclass, field

from .player import Player


@dataclass
class Club:
    """Un club: nombre, plantilla y finanzas basicas."""

    name: str
    short_name: str
    players: list[Player] = field(default_factory=list)
    budget: int = 0

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
