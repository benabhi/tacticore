"""Eventos del partido: registro estructurado de lo que va pasando.

Cada momento relevante (remate, gol, quite, atajada, falta, ...) se guarda como
un `MatchEvent` con su protagonista. Es la base para el relato en pantalla, las
stats en vivo y, mas adelante, un sistema de narracion con variantes (ver
docs/DESIGN.md). El motor solo registra el evento estructurado; el TEXTO lo
arma `narration.py` (asi se puede enriquecer sin tocar la simulacion).
"""

from dataclasses import dataclass

from .entities import Side


@dataclass
class MatchEvent:
    """Un evento del partido, con el tick/reloj y quien lo protagonizo."""

    tick: int
    clock: float
    kind: str               # "gol", "remate", "quite", "atajada", ...
    team: Side | None = None
    player: str | None = None  # nombre para mostrar del protagonista (si aplica)
