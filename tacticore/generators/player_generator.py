"""Generador de jugadores de fantasia.

La calidad depende del nivel de liga (`LeagueTier`): la liga A genera a los
mejores y la E a los mas flojos. Para cada atributo el valor sale de:

    base_del_tier + offset_por_posicion + talento_individual + ruido

Escala 1-100 con decimales. Asi un jugador NO tiene todos los atributos en la
misma banda (un arquero tiene reflejos altos pero remate bajo), los minimos
suben en las ligas mejores, y hay cracks (talento alto) en cualquier liga.
"""

import random
from datetime import date

from .. import config
from ..domain.enums import Foot, LeagueTier, Morale, Position, Specialty
from ..domain.player import ALL_ATTRS, Player
from ..domain.positions import POSITION_PRIORITIES, Line, line_of
from .name_generator import NameGenerator

# Nivel base de un atributo "neutro" segun el nivel de la liga (1-100).
_TIER_BASE: dict[LeagueTier, float] = {
    LeagueTier.A: 78.0,
    LeagueTier.B: 66.0,
    LeagueTier.C: 54.0,
    LeagueTier.D: 44.0,
    LeagueTier.E: 35.0,
}

# Offset por posicion, derivado de los atributos prioritarios (domain/positions):
# los prioritarios suben (por ranking), el resto baja un poco (especializacion).
# El arquero ademas hunde las habilidades de jugador de campo, asi sigue siendo
# muy bueno bajo los palos pero malo afuera.
_PRIORITY_BOOST = (14, 10, 7, 5, 3)   # offset por ranking del atributo prioritario
_OFF_PENALTY = -8.0                    # atributos no prioritarios: leve bajada
_GK_OUTFIELD = ("shooting", "dribbling", "crossing", "passing", "tackling")
_GK_OUTFIELD_PENALTY = -28.0


def _build_role_offsets() -> dict[Position, dict[str, float]]:
    table: dict[Position, dict[str, float]] = {}
    for position, priorities in POSITION_PRIORITIES.items():
        offsets = {attr: _OFF_PENALTY for attr in ALL_ATTRS}
        for i, attr in enumerate(priorities):
            offsets[attr] = float(_PRIORITY_BOOST[i])
        if position is Position.GOALKEEPER:
            for attr in _GK_OUTFIELD:
                offsets[attr] = _GK_OUTFIELD_PENALTY
        table[position] = offsets
    return table


_ROLE_OFFSETS = _build_role_offsets()

_NOISE = 5.0  # ruido por atributo (+/-)

# Probabilidad de que un jugador tenga especialidad (0-1) y de que tenga apodo.
_SPECIALTY_CHANCE = 0.35
_NICKNAME_CHANCE = 0.08


def _clamp(value: float) -> float:
    """Acota a 1.0-100.0 y redondea a un decimal."""
    return round(max(1.0, min(100.0, value)), 1)


class PlayerGenerator:
    """Crea jugadores con atributos, fisico, estado y rasgos (deterministas)."""

    def __init__(
        self,
        rng: random.Random | None = None,
        names: NameGenerator | None = None,
    ) -> None:
        self._rng = rng or random.Random()
        # Comparte el mismo rng con el generador de nombres para mantener el
        # determinismo en una sola cadena de azar.
        self._names = names or NameGenerator(self._rng)

    def generate(
        self,
        position: Position | None = None,
        tier: LeagueTier = LeagueTier.C,
        country_code: str | None = None,
        today: date | None = None,
    ) -> Player:
        """Genera un jugador de la liga `tier`.

        Si no se da `position`, se elige al azar. El `tier` define la calidad
        general (la liga A es la mejor, la E la mas floja). `country_code` define
        la nacionalidad (nombres y campo `nationality`). `today` es la fecha del
        juego, contra la que se ancla la fecha de nacimiento (default: inicio de
        temporada).
        """
        today = today or config.SEASON_START_DATE
        rng = self._rng
        pos = position or rng.choice(list(Position))
        base = _TIER_BASE[tier]
        offsets = _ROLE_OFFSETS[pos]
        # Talento individual: corre todos los atributos del jugador hacia
        # arriba o abajo (cracks vs jugadores del monton dentro de su liga).
        talent = rng.uniform(-5, 10)

        attrs = {}
        for attr in ALL_ATTRS:
            offset = offsets.get(attr, 0.0)
            attrs[attr] = _clamp(base + offset + talent + rng.uniform(-_NOISE, _NOISE))

        # Fecha de nacimiento: se elige una edad objetivo y se ancla a `today`
        # con mes/dia al azar (asi los cumpleanios quedan repartidos en el anio).
        target_age = rng.randint(16, 36)
        birth_date = date(today.year - target_age, rng.randint(1, 12), rng.randint(1, 28))
        # Arqueros y defensores suelen ser mas altos.
        if line_of(pos) in (Line.GOALKEEPER, Line.DEFENSE):
            height = rng.randint(180, 200)
        else:
            height = rng.randint(165, 190)
        weight = height - 100 + rng.randint(-5, 8)
        # Experiencia: sube con la edad (un pibe arranca bajo, un veterano alto).
        experience = _clamp((target_age - 15) * 4.5 + rng.uniform(-6, 6))

        first, last = self._names.player_first_last(country_code)
        specialty = (
            rng.choice(list(Specialty)) if rng.random() < _SPECIALTY_CHANCE else None
        )
        nickname = (
            self._names.nickname() if rng.random() < _NICKNAME_CHANCE else None
        )

        player = Player(
            first_name=first,
            last_name=last,
            nationality=country_code or "FAN",
            position=pos,
            # El pie derecho es el mas comun; ambos, el mas raro.
            foot=rng.choices(list(Foot), weights=[3, 6, 1])[0],
            birth_date=birth_date,
            height_cm=height,
            weight_kg=weight,
            **attrs,
            form=_clamp(rng.uniform(40, 80)),
            fitness=100.0,
            experience=experience,
            morale=rng.choices(list(Morale), weights=[1, 2, 4, 3, 2])[0],
            specialty=specialty,
            nickname=nickname,
            injury_proneness=_clamp(rng.uniform(10, 80)),
        )

        # El potencial es un techo por encima del nivel actual; los jovenes
        # tienen mas margen de crecimiento.
        age = player.age_on(today)
        growth_room = max(0.0, (24 - age)) * 1.2 + rng.uniform(0, 5)
        player.potential = _clamp(player.overall + growth_room)
        # Rasgos de personalidad 1-5 (sesgados al centro, como la moral).
        player.leadership = rng.choices([1, 2, 3, 4, 5], weights=[1, 2, 4, 3, 2])[0]
        player.character = rng.choices([1, 2, 3, 4, 5], weights=[1, 2, 4, 3, 2])[0]
        return player

    # Tope duro del potencial de un juvenil por encima de la base del tier: alto
    # margen de crecimiento pero NUNCA desbocado (nunca 99). Ver docs de balance.
    _YOUTH_POT_MARGIN = 25
    _YOUTH_POT_HARD_CAP = 95

    def generate_youth(
        self,
        tier: LeagueTier = LeagueTier.D,
        scout_skill: float = 50.0,
        country_code: str | None = None,
        today: date | None = None,
        position: Position | None = None,
        quality_bonus: float = 0.0,
    ) -> Player:
        """Genera un JUVENIL (15-18) crudo pero con potencial alto y acotado.

        El juvenil rinde poco HOY (nivel actual bajo) pero tiene mucho margen de
        crecimiento y entrena rapido por su edad. Trae un atributo DESTACADO
        (prioritario de su posicion) de forma moderada. La calidad del ojeador
        (`scout_skill`, 1-100) y el `quality_bonus` del Complejo juvenil elevan el
        potencial (con tope duro). Determinista con el rng que se le paso.
        """
        today = today or config.SEASON_START_DATE
        rng = self._rng
        pos = position or rng.choice(list(Position))
        base = _TIER_BASE[tier]
        offsets = _ROLE_OFFSETS[pos]

        # Potencial (techo): base del tier + calidad del ojeador + edificio, acotado.
        scout_factor = (max(1.0, min(100.0, scout_skill)) / 100.0) * 22.0
        ceiling = min(self._YOUTH_POT_HARD_CAP, base + self._YOUTH_POT_MARGIN)
        potential = _clamp(min(ceiling, base + scout_factor + quality_bonus + rng.uniform(-4, 4)))

        # Nivel ACTUAL: bien por DEBAJO del potencial (rinde poco hoy, mucho por crecer).
        current = potential - rng.uniform(16, 28)
        raw = current - 6.0  # los prioritarios suben por sus offsets -> overall ~ current
        talent = rng.uniform(-3, 5)
        attrs = {}
        for attr in ALL_ATTRS:
            v = raw + offsets.get(attr, 0.0) + talent + rng.uniform(-_NOISE, _NOISE)
            attrs[attr] = _clamp(min(potential - 2, v))  # ningun atributo por encima del techo
        # Un atributo DESTACADO (prioritario de la posicion), subida moderada y bajo el techo.
        standout = POSITION_PRIORITIES[pos][0]
        attrs[standout] = _clamp(min(potential - 2, attrs[standout] + rng.uniform(7, 13)))

        age = rng.randint(15, 18)
        # Cumpleanios ya cumplido este anio (mes/dia <= hoy) -> la edad efectiva
        # (age_on) coincide exacto con `age` y el juvenil queda en la banda 15-18.
        month = rng.randint(1, today.month)
        day = rng.randint(1, 28) if month < today.month else rng.randint(1, min(28, today.day))
        birth_date = date(today.year - age, month, day)
        if line_of(pos) in (Line.GOALKEEPER, Line.DEFENSE):
            height = rng.randint(178, 198)
        else:
            height = rng.randint(165, 190)
        weight = height - 100 + rng.randint(-6, 6)

        first, last = self._names.player_first_last(country_code)
        specialty = (
            rng.choice(list(Specialty)) if rng.random() < _SPECIALTY_CHANCE * 0.5 else None
        )

        player = Player(
            first_name=first, last_name=last, nationality=country_code or "FAN",
            position=pos, foot=rng.choices(list(Foot), weights=[3, 6, 1])[0],
            birth_date=birth_date, height_cm=height, weight_kg=weight, **attrs,
            form=_clamp(rng.uniform(40, 65)), fitness=100.0,
            experience=_clamp((age - 15) * 3.0 + rng.uniform(0, 4)),  # verde
            morale=rng.choices(list(Morale), weights=[1, 2, 4, 3, 2])[0],
            specialty=specialty,
            injury_proneness=_clamp(rng.uniform(10, 70)),
        )
        player.potential = potential
        player.leadership = rng.choices([1, 2, 3, 4, 5], weights=[2, 3, 4, 2, 1])[0]
        player.character = rng.choices([1, 2, 3, 4, 5], weights=[2, 3, 4, 2, 1])[0]
        return player
