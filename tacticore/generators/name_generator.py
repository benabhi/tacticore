"""Generador de nombres de fantasia basado en silabas."""

import random

from .data import name_data
from .name_pools import load_pool

# Palabras que son descriptores (prefijo/sufijo), no el toponimo inventado. Sirve
# para extraer el nucleo de un nombre de club (p. ej. el estadio se nombra asi).
_CLUB_DESCRIPTORS = set(name_data.CLUB_PREFIXES) | set(name_data.CLUB_SUFFIXES)


def club_core(name: str) -> str:
    """Devuelve el toponimo (la pieza inventada) de un nombre de club.

    Un nombre tiene exactamente un toponimo entre descriptores genericos
    ("Real Caldton United" -> "Caldton"). Si no hubiera, cae a la ultima palabra.
    """
    for word in name.split():
        if word not in _CLUB_DESCRIPTORS:
            return word
    return name.split()[-1]


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
        """Devuelve un alias al azar (ej. 'La Pulga', 'El Toro Negro').

        Se arma como "El/La <sustantivo> [<adjetivo>]", con concordancia de
        genero. Hay ~1000 alias posibles, asi se repiten poco.
        """
        if self._rng.random() < 0.5:
            article, nouns, adjs = "El", name_data.NICK_EL_NOUNS, name_data.NICK_EL_ADJ
        else:
            article, nouns, adjs = "La", name_data.NICK_LA_NOUNS, name_data.NICK_LA_ADJ
        noun = self._rng.choice(nouns)
        if self._rng.random() < 0.45:
            return f"{article} {noun} {self._rng.choice(adjs)}"
        return f"{article} {noun}"

    def fan_group_name(self) -> str:
        """Devuelve un nombre de hinchada / grupo de fans (ej. 'La Furia Roja')."""
        roll = self._rng.random()
        if roll < 0.22:
            return "Los " + self._rng.choice(name_data.FAN_ANIMALS)
        if roll < 0.40:
            return "Los " + self._rng.choice(name_data.FAN_ADJECTIVES)
        if roll < 0.58:
            animal = self._rng.choice(name_data.FAN_ANIMALS)
            return f"Los {animal} {self._rng.choice(name_data.FAN_ADJECTIVES)}"
        if roll < 0.72:
            return "La " + self._rng.choice(name_data.FAN_LA_NOUNS)
        if roll < 0.90:
            noun = self._rng.choice(name_data.FAN_LA_NOUNS)
            return f"La {noun} {self._rng.choice(name_data.FAN_FEM_MODIFIERS)}"
        collective = self._rng.choice(name_data.FAN_MASC_COLLECTIVE)
        return f"{collective} {self._rng.choice(name_data.FAN_MASC_MODIFIERS)}"

    def club_name(self) -> str:
        """Devuelve un nombre de club de fantasia.

        Combina un toponimo inventado con descriptores genericos en distintos
        patrones (prefijo, sufijo, ambos o ninguno) para dar variedad. El espacio
        posible es de varios millones de nombres.
        """
        place = self._build_toponym()
        roll = self._rng.random()
        if roll < 0.40:                                   # "Real Caldton"
            return f"{self._rng.choice(name_data.CLUB_PREFIXES)} {place}"
        if roll < 0.75:                                   # "Caldton United"
            return f"{place} {self._rng.choice(name_data.CLUB_SUFFIXES)}"
        if roll < 0.88:                                   # "Real Caldton United"
            pre = self._rng.choice(name_data.CLUB_PREFIXES)
            suf = self._rng.choice(name_data.CLUB_SUFFIXES)
            return f"{pre} {place} {suf}"
        return place                                      # "Caldton" (solo)

    def club_names(self, count: int) -> list[str]:
        """Devuelve `count` nombres de club UNICOS (sin repetir entre si)."""
        seen: set[str] = set()
        out: list[str] = []
        guard = 0
        while len(out) < count and guard < count * 50 + 100:
            guard += 1
            name = self.club_name()
            if name not in seen:
                seen.add(name)
                out.append(name)
        return out

    def _build_toponym(self) -> str:
        """Arma un toponimo inventado: comienzo + infijo opcional + final."""
        word = self._rng.choice(name_data.TOPO_HEADS)
        if self._rng.random() < 0.45:
            word = self._join(word, self._rng.choice(name_data.TOPO_INFIXES))
        return self._join(word, self._rng.choice(name_data.TOPO_TAILS))

    @staticmethod
    def _join(a: str, b: str) -> str:
        """Une dos piezas evitando duplicar la letra del borde (Nord+dale=Nordale)."""
        if a and b and a[-1].lower() == b[0].lower():
            return a + b[1:]
        return a + b

    def _build_word(self, syllables: list[str], lo: int, hi: int) -> str:
        """Concatena entre `lo` y `hi` silabas y capitaliza el resultado."""
        count = self._rng.randint(lo, hi)
        word = "".join(self._rng.choice(syllables) for _ in range(count))
        return word.capitalize()
