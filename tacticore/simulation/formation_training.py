"""Entrenamiento de formaciones (familiaridad con cada tactica, escala 1-100).

Cada formacion tiene, para el club del jugador, un nivel de entrenamiento que sube
cuanto mas se juega con ella (estilo Hattrick). El punto de partida lo define la
MENTALIDAD del DT: un DT ofensivo arranca mejor entrenadas las formaciones ofensivas
(y peor las defensivas), uno defensivo al reves, y uno neutral todas a un nivel
decente pero por debajo de esos picos. Que la formacion sea "ofensiva" o "defensiva"
se deriva de sus slots (cuan adelantado juega el equipo). Funciones puras, sin UI.

El EFECTO del nivel en el resultado del partido se agrega mas adelante; aca solo se
maneja el atributo y su progresion.
"""

from ..domain.club import Club
from ..domain.coach import Coach
from ..domain.enums import Mentality
from ..domain.positions import is_goalkeeper
from .match.formation import FORMATIONS, get_formation

_NEUTRAL_BASE = 35.0   # nivel de todas las formaciones con un DT neutral
_BIAS_AMP = 22.0       # cuanto sube/baja el pico segun la mentalidad del DT
_BASE_GAIN = 8.0       # ganancia base de entrenamiento por partido jugado


def _clamp(value: float) -> float:
    return round(max(1.0, min(100.0, value)), 1)


def _avg_relx(formation) -> float:
    """Promedio de rel_x de los jugadores de campo (cuan adelantado juega el equipo)."""
    outfield = [s for s in formation.slots if not is_goalkeeper(s.position)]
    return sum(s.rel_x for s in outfield) / len(outfield)


# rel_x promedio de cada formacion, y su rango, para normalizar la "ofensividad".
_AVG_RELX = {f.name: _avg_relx(f) for f in FORMATIONS}
_LO, _HI = min(_AVG_RELX.values()), max(_AVG_RELX.values())


def offensiveness(name: str) -> float:
    """0 = mas defensiva, 1 = mas ofensiva (normalizado sobre las formaciones)."""
    avg = _AVG_RELX.get(name)
    if avg is None:
        avg = _avg_relx(get_formation(name))
    return (avg - _LO) / (_HI - _LO) if _HI > _LO else 0.5


def initial_training(mentality: Mentality) -> dict[str, float]:
    """Nivel inicial de cada formacion segun la mentalidad del DT."""
    result: dict[str, float] = {}
    for f in FORMATIONS:
        if mentality is Mentality.NEUTRAL:
            level = _NEUTRAL_BASE
        else:
            bias = offensiveness(f.name) * 2 - 1  # -1 (def) .. +1 (off)
            if mentality is Mentality.DEFENSIVE:
                bias = -bias
            level = _NEUTRAL_BASE + _BIAS_AMP * bias
        result[f.name] = _clamp(level)
    return result


def ensure_all(club: Club) -> None:
    """Completa las formaciones que falten en el club (default = nivel neutral)."""
    for f in FORMATIONS:
        club.formation_training.setdefault(f.name, _NEUTRAL_BASE)


def training_level(club: Club, name: str) -> float:
    """Nivel de entrenamiento del club con la formacion `name`."""
    return club.formation_training.get(name, _NEUTRAL_BASE)


def train_formation(club: Club, name: str, coach: Coach | None) -> None:
    """Sube el entrenamiento de una formacion al jugar con ella (rinde menos cerca
    de 100; un DT con mas habilidad y el Centro de entrenamiento entrenan mas rapido)."""
    from .facilities import training_boost

    level = club.formation_training.get(name, _NEUTRAL_BASE)
    skill = coach.skill if coach else 40.0
    gain = _BASE_GAIN * (0.6 + skill / 100) * (100 - level) / 100 * training_boost(club)
    club.formation_training[name] = _clamp(level + gain)
