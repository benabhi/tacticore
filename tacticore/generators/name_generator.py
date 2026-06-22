"""Generador de nombres de fantasia basado en silabas."""

import random

from .data import name_data
from .name_pools import load_pool


class NameGenerator:
    """Arma nombres de jugadores y clubes.

    Los clubes son de fantasia (silabas inventadas). Los jugadores usan nombres
    reales por nacionalidad si hay pool para el pais (mezclando nombre + apellido
    de personas distintas, asi no se reproducen personas reales); si no, caen al
    fallback silabico.

    Recibe un `random.Random` para ser determinista. Si no se pasa, crea uno
    propio no determinista.
    """

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()

    def player_first_last(
        self, country_code: str | None = None
    ) -> tuple[str, str]:
        """Devuelve (nombre, apellido). Por nacionalidad si hay pool del pais."""
        if country_code is not None:
            pool = load_pool(country_code)
            if pool is not None:
                first_names, last_names = pool
                return self._rng.choice(first_names), self._rng.choice(last_names)
        # Fallback: nombres de fantasia con silabas.
        first = self._build_word(name_data.FIRST_SYLLABLES, 2, 3)
        last = self._build_word(name_data.LAST_SYLLABLES, 2, 3)
        return first, last

    def player_name(self) -> str:
        """Devuelve un nombre completo de jugador (nombre + apellido)."""
        first, last = self.player_first_last()
        return f"{first} {last}"

    def nickname(self) -> str:
        """Devuelve un apodo al azar (ej. 'La Pulga')."""
        return self._rng.choice(name_data.NICKNAMES)

    def club_name(self) -> str:
        """Devuelve un nombre de club (prefijo + nucleo inventado)."""
        prefix = self._rng.choice(name_data.CLUB_PREFIXES)
        core = self._build_word(name_data.CLUB_SYLLABLES, 2, 3)
        return f"{prefix} {core}"

    def _build_word(self, syllables: list[str], lo: int, hi: int) -> str:
        """Concatena entre `lo` y `hi` silabas y capitaliza el resultado."""
        count = self._rng.randint(lo, hi)
        word = "".join(self._rng.choice(syllables) for _ in range(count))
        return word.capitalize()
