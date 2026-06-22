"""Generador de nombres de fantasia basado en silabas."""

import random

from .data import name_data


class NameGenerator:
    """Arma nombres ficticios de jugadores y clubes combinando silabas.

    Recibe un `random.Random` para ser determinista. Si no se pasa, crea uno
    propio no determinista.
    """

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()

    def player_first_last(self) -> tuple[str, str]:
        """Devuelve (nombre, apellido) por separado."""
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
