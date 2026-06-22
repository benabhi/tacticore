"""Motor de simulacion de un partido.

ESQUELETO: recibira dos clubes y un `random.Random` y devolvera un `Match`
con el resultado calculado a partir de los atributos de las plantillas. No
imprime ni toca la UI.
"""

import random

from ..domain.club import Club
from ..domain.match import Match


def simulate_match(home: Club, away: Club, rng: random.Random) -> Match:
    """Simula un partido y devuelve el resultado.

    TODO: calcular goles segun overall/atributos de cada plantilla. Por ahora
    devuelve un marcador placeholder 0-0 sin jugar.
    """
    return Match(home=home, away=away)
