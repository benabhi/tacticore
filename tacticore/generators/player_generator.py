"""Generador de jugadores de fantasia."""

import random

from ..domain.enums import Foot, Morale, Position, Specialty
from ..domain.player import Player
from .name_generator import NameGenerator

# Los 7 skills principales.
_SKILLS = (
    "goalkeeping", "defending", "playmaking", "winger", "passing", "scoring",
    "set_pieces",
)

# Rango (min, max) de cada skill segun la posicion natural. Los skills no
# listados usan _DEFAULT_RANGE (valores bajos). Asi un arquero tiene goalkeeping
# alto y scoring bajo, un delantero al reves, etc.
_DEFAULT_RANGE = (1, 7)
_POSITION_PROFILE: dict[Position, dict[str, tuple[int, int]]] = {
    Position.GOALKEEPER: {
        "goalkeeping": (10, 20), "defending": (3, 9), "set_pieces": (2, 9),
        "passing": (3, 9),
    },
    Position.DEFENDER: {
        "defending": (10, 20), "playmaking": (5, 13), "passing": (6, 14),
        "winger": (3, 12), "set_pieces": (3, 12), "scoring": (2, 8),
    },
    Position.MIDFIELDER: {
        "playmaking": (10, 20), "passing": (9, 18), "winger": (5, 15),
        "scoring": (5, 14), "set_pieces": (4, 14), "defending": (5, 13),
    },
    Position.FORWARD: {
        "scoring": (10, 20), "passing": (6, 15), "winger": (6, 15),
        "set_pieces": (4, 13), "playmaking": (5, 13), "defending": (2, 8),
    },
}

# Probabilidad de que un jugador tenga especialidad (0-1) y de que tenga apodo.
_SPECIALTY_CHANCE = 0.35
_NICKNAME_CHANCE = 0.08


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

    def generate(self, position: Position | None = None) -> Player:
        """Genera un jugador; si no se da `position`, se elige al azar."""
        rng = self._rng
        pos = position or rng.choice(list(Position))
        profile = _POSITION_PROFILE[pos]

        # Skills principales segun el perfil de la posicion.
        skills = {s: rng.randint(*profile.get(s, _DEFAULT_RANGE)) for s in _SKILLS}

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
        player.potential = min(20, player.overall + rng.randint(0, 3) + growth)
        return player
