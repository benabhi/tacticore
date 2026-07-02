"""Entidad Tactica: el planteo del equipo para UN partido.

Se asigna por partido (cada encuentro tiene su propia tactica). Guarda la
mentalidad, la tactica general, el marcaje, la formacion (por nombre) y la
seleccion de jugadores: `lineup` son los 11 titulares alineados a los slots de la
formacion (puede haber huecos = None) y `bench` los suplentes (banco de extras).

La pantalla donde se arma (planteo + cancha, en una sola vista) es
`ui/screens/tactic_screen.py`.
"""

from dataclasses import dataclass, field

from .enums import Marking, Mentality, TeamTactic
from .player import Player


@dataclass
class Tactic:
    """Planteo de un equipo para un partido concreto."""

    mentality: Mentality = Mentality.NEUTRAL
    team_tactic: TeamTactic = TeamTactic.NORMAL
    formation: str = "4-3-3"                            # nombre de la formacion
    lineup: list[Player | None] = field(default_factory=list)  # titulares, por slot
    bench: list[Player | None] = field(default_factory=list)   # suplentes (banco)
    marking: Marking = Marking.ZONAL                    # esquema de marcaje del equipo

    @property
    def is_complete(self) -> bool:
        """True si los 11 titulares estan cubiertos (sin huecos)."""
        return bool(self.lineup) and all(p is not None for p in self.lineup)
