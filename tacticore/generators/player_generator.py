"""Generador de jugadores de fantasia.

La calidad depende del nivel de liga (`LeagueTier`): la liga A genera a los
mejores y la E a los mas flojos. Para cada skill el valor sale de:

    base_del_tier + offset_por_posicion + talento_individual + ruido

asi un jugador NO tiene todos los skills en el mismo rango: un arquero de la
liga E puede tener porteria ~6-9 pero regate/definicion en 1. Esos minimos
suben de a poco en las ligas mejores (porque sube el base), y ademas hay cracks
(talento alto) dentro de cualquier liga. El `overall` (OVR) resume todo eso.
"""

import random

from ..domain.enums import Foot, LeagueTier, Morale, Position, Specialty
from ..domain.player import Player
from .name_generator import NameGenerator

# Los 7 skills principales.
_SKILLS = (
    "goalkeeping", "defending", "playmaking", "winger", "passing", "scoring",
    "set_pieces",
)

# Nivel base de un skill PRINCIPAL segun el nivel de la liga.
_TIER_BASE: dict[LeagueTier, int] = {
    LeagueTier.A: 14,
    LeagueTier.B: 12,
    LeagueTier.C: 10,
    LeagueTier.D: 8,
    LeagueTier.E: 6,
}

# Cuanto sube/baja cada skill respecto del base segun la posicion. Lo que no
# esta listado usa _IRRELEVANT_OFFSET (skills que no van con el puesto, quedan
# muy bajos). Esto es lo que da la variedad dentro de un mismo jugador.
_IRRELEVANT_OFFSET = -8
_ROLE_OFFSETS: dict[Position, dict[str, int]] = {
    Position.GOALKEEPER: {
        "goalkeeping": 4, "defending": -2, "set_pieces": -4, "passing": -4,
        "playmaking": -6, "winger": -9, "scoring": -9,
    },
    Position.DEFENDER: {
        "defending": 3, "playmaking": -1, "passing": 0, "winger": -2,
        "set_pieces": -2, "scoring": -5, "goalkeeping": -12,
    },
    Position.MIDFIELDER: {
        "playmaking": 3, "passing": 2, "winger": 0, "scoring": -1,
        "defending": -1, "set_pieces": -1, "goalkeeping": -12,
    },
    Position.FORWARD: {
        "scoring": 3, "passing": 0, "winger": 0, "set_pieces": -1,
        "playmaking": -1, "defending": -5, "goalkeeping": -12,
    },
}

# Probabilidad de que un jugador tenga especialidad (0-1) y de que tenga apodo.
_SPECIALTY_CHANCE = 0.35
_NICKNAME_CHANCE = 0.08


def _clamp_skill(value: int) -> int:
    """Acota un skill al rango valido 1-20."""
    return max(1, min(20, value))


class PlayerGenerator:
    """Crea jugadores con skills, fisico, estado y rasgos (deterministas)."""

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
    ) -> Player:
        """Genera un jugador de la liga `tier`.

        Si no se da `position`, se elige al azar. El `tier` define la calidad
        general (la liga A es la mejor, la E la mas floja).
        """
        rng = self._rng
        pos = position or rng.choice(list(Position))
        base = _TIER_BASE[tier]
        offsets = _ROLE_OFFSETS[pos]
        # Talento individual: algunos jugadores destacan dentro de su liga.
        talent = rng.randint(-2, 3)

        skills = {}
        for skill in _SKILLS:
            offset = offsets.get(skill, _IRRELEVANT_OFFSET)
            skills[skill] = _clamp_skill(base + offset + talent + rng.randint(-2, 2))

        age = rng.randint(16, 36)
        # Arqueros y defensores suelen ser mas altos.
        if pos in (Position.GOALKEEPER, Position.DEFENDER):
            height = rng.randint(180, 200)
        else:
            height = rng.randint(165, 190)
        weight = height - 100 + rng.randint(-5, 8)

        first, last = self._names.player_first_last()
        specialty = (
            rng.choice(list(Specialty)) if rng.random() < _SPECIALTY_CHANCE else None
        )
        nickname = (
            self._names.nickname() if rng.random() < _NICKNAME_CHANCE else None
        )

        player = Player(
            first_name=first,
            last_name=last,
            position=pos,
            # El pie derecho es el mas comun; ambos, el mas raro.
            foot=rng.choices(list(Foot), weights=[3, 6, 1])[0],
            age=age,
            height_cm=height,
            weight_kg=weight,
            **skills,
            stamina=rng.randint(6, 18),
            # La experiencia crece con la edad.
            experience=min(20, max(1, (age - 16) // 2 + rng.randint(0, 4))),
            leadership=rng.randint(2, 16),
            form=rng.randint(6, 16),
            fitness=100,
            morale=rng.choices(list(Morale), weights=[1, 2, 4, 3, 2])[0],
            specialty=specialty,
            nickname=nickname,
            injury_proneness=rng.randint(3, 18),
        )

        # El potencial es un techo por encima del nivel actual; los jovenes
        # tienen mas margen de crecimiento.
        growth = max(0, (24 - age)) // 2
        player.potential = _clamp_skill(player.overall + rng.randint(0, 3) + growth)
        return player
