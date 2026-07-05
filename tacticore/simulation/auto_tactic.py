"""Tactica por defecto: se arma sola cuando el jugador no planteo el partido.

Si el manager avanza hasta el dia del partido sin haber armado la tactica, el
juego coloca una automatica:

- la ALINEACION sale por puesto y overall (`auto_select`, el mejor para cada slot);
- la FORMACION se elige segun la MENTALIDAD del DT: un DT ofensivo juega una
  formacion ofensiva, uno defensivo una defensiva y uno neutral una equilibrada.
  Dentro de esa categoria se toma la mejor entrenada del club (ver
  `formation_training`), asi el DT juega lo que mejor sabe;
- la TACTICA general va al azar (determinista por el `rng` que se recibe).

Funcion pura: misma semilla -> misma tactica. Sin UI.
"""

import random

from ..domain.club import Club
from ..domain.enums import Marking, Mentality, Specialty, TeamTactic
from ..domain.player import Player
from ..domain.tactic import Tactic
from .formation_training import offensiveness, training_level
from .match.formation import FORMATIONS, auto_select, get_formation

# Umbrales de "ofensividad" (0 = mas defensiva .. 1 = mas ofensiva) para agrupar
# las 8 formaciones en defensivas / equilibradas / ofensivas (reparto 3/2/3).
_DEF_MAX = 0.33
_OFF_MIN = 0.66

# El balon parado no tiene atributo propio: se estima con el remate mas un bonus
# para el especialista en pelota parada ("Canonero" / DEAD_BALL).
_DEAD_BALL_BONUS = 12.0


def set_piece_skill(player: Player) -> float:
    """Aptitud para el balon parado (tiros libres/corners/penales)."""
    base = player.shooting
    if player.specialty is Specialty.DEAD_BALL:
        base += _DEAD_BALL_BONUS
    return base


def default_captain(starters: list[Player]) -> Player | None:
    """Capitan por defecto: el titular con mas experiencia (desempata liderazgo)."""
    if not starters:
        return None
    return max(starters, key=lambda p: (p.experience, p.leadership))


def default_free_kick_taker(starters: list[Player]) -> Player | None:
    """Encargado del balon parado por defecto: el titular con mejor pelota parada."""
    if not starters:
        return None
    return max(starters, key=set_piece_skill)


def _category_formations(mentality: Mentality) -> list[str]:
    """Nombres de formacion que le corresponden a la mentalidad del DT."""
    names = [f.name for f in FORMATIONS]
    if mentality is Mentality.OFFENSIVE:
        return [n for n in names if offensiveness(n) >= _OFF_MIN]
    if mentality is Mentality.DEFENSIVE:
        return [n for n in names if offensiveness(n) <= _DEF_MAX]
    return [n for n in names if _DEF_MAX < offensiveness(n) < _OFF_MIN]


def default_tactic(club: Club, rng: random.Random) -> Tactic:
    """Arma una tactica automatica para `club`.

    Formacion segun la mentalidad del DT (la mejor entrenada de esa categoria),
    alineacion por overall y tactica general al azar.
    """
    mentality = club.coach.mentality if club.coach else Mentality.NEUTRAL
    candidates = _category_formations(mentality) or [f.name for f in FORMATIONS]
    # Dentro de la categoria, la mejor entrenada (empate -> la primera de la lista).
    formation_name = max(candidates, key=lambda n: training_level(club, n))
    formation = get_formation(formation_name)
    lineup, bench = auto_select(club, formation)
    starters = [p for p in lineup if p is not None]
    return Tactic(
        mentality=mentality,
        team_tactic=rng.choice(list(TeamTactic)),
        formation=formation_name,
        lineup=list(lineup),
        bench=list(bench),
        marking=Marking.ZONAL,
        captain=default_captain(starters),
        free_kick_taker=default_free_kick_taker(starters),
    )
