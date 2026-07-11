"""Forma de los jugadores: sube al jugar, baja al no jugar (por participacion).

Cada partido de LIGA del club del jugador mueve la forma del plantel: los que
estuvieron en el once SUBEN (con un extra si el equipo gano) y los que se quedaron
afuera BAJAN. La forma (`Player.form`, 1-100) ya pesa en el valor/sueldo del jugador
(ver `economy`), asi que mantener a la gente jugando importa. Logica pura (sin UI);
solo toca al club del jugador. Se llama desde `daily.finish_player_match`.
"""

from ..domain.club import Club
from ..domain.match import Match

# Cuanto se mueve la forma por semana (tunable).
FORM_PLAYED = 5.0   # subida de los que jugaron el partido
FORM_WIN = 2.0      # extra para los que jugaron si el equipo gano
FORM_BENCH = 4.0    # bajada de los que NO jugaron


def _clamp(value: float) -> float:
    return round(max(1.0, min(100.0, value)), 1)


def _effective_lineup(club: Club, match: Match) -> list:
    """El once que jugo: la tactica si esta completa; si no, el top-11 por overall
    (mismo criterio que usa el motor estadistico para la 'fuerza')."""
    tactic = match.tactic
    if tactic is not None and tactic.is_complete:
        return [p for p in tactic.lineup if p is not None]
    return sorted(club.players, key=lambda p: p.overall, reverse=True)[:11]


def update_after_match(game, match: Match) -> None:
    """Mueve la forma del plantel del jugador tras su partido de liga (por participacion)."""
    pc = game.player_club
    if pc is None or pc not in (match.home, match.away):
        return
    played = {id(p) for p in _effective_lineup(pc, match)}
    gf, ga = ((match.home_goals, match.away_goals) if match.home is pc
              else (match.away_goals, match.home_goals))
    won = gf > ga
    for p in pc.players:
        if id(p) in played:
            p.form = _clamp(p.form + FORM_PLAYED + (FORM_WIN if won else 0.0))
        else:
            p.form = _clamp(p.form - FORM_BENCH)
