"""Aleatoriedad determinista.

Unica fuente de azar del juego. NO se usa el `random` global del modulo: se
crea una instancia propia con semilla para poder reproducir una partida exacta
(misma semilla -> mismo mundo y mismos resultados).
"""

import random


def new_rng(seed: int | None = None) -> random.Random:
    """Crea un generador aleatorio propio.

    Si `seed` es None, queda no determinista (semilla del sistema). Para una
    partida reproducible, pasar siempre una semilla entera.
    """
    return random.Random(seed)
