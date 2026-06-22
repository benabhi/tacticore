"""Generador del mundo completo (paises -> ligas -> clubes -> jugadores).

Es el orquestador de los generadores chicos. Acepta un callback de progreso
para alimentar la pantalla de carga estilo Caves of Qud. Determinista por seed.
"""

import random
from collections.abc import Callable

from .. import config
from ..domain.country import Country
from ..domain.enums import LeagueTier
from ..domain.league import League
from .club_generator import ClubGenerator
from .data import country_data
from .name_generator import NameGenerator

# Firma del callback de progreso: (texto, hechos, total).
ProgressCallback = Callable[[str, int, int], None]


class WorldGenerator:
    """Genera el mundo entero a partir de una semilla."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()
        self._names = NameGenerator(self._rng)
        self._clubs = ClubGenerator(self._rng, self._names)

    def generate(self, progress: ProgressCallback | None = None) -> list[Country]:
        """Genera y devuelve la lista de paises con todo su contenido.

        Si se pasa `progress`, se lo llama tras cada club generado con un texto
        descriptivo, la cantidad hecha y el total (para la barra de carga).
        """
        selected = country_data.COUNTRIES[: config.WORLD_COUNTRY_COUNT]
        clubs_per_league = config.CLUBS_PER_LEAGUE
        total_clubs = len(selected) * len(LeagueTier) * clubs_per_league

        countries: list[Country] = []
        done = 0
        for country_name, country_code in selected:
            country = Country(name=country_name, code=country_code)
            for tier in LeagueTier:
                league = League(
                    name=f"{country_name} Liga {tier.value}",
                    tier=tier,
                    country_code=country_code,
                )
                for _ in range(clubs_per_league):
                    club = self._clubs.generate(
                        squad_size=config.SQUAD_SIZE,
                        country_code=country_code,
                        tier=tier,
                    )
                    league.clubs.append(club)
                    done += 1
                    if progress is not None:
                        progress(
                            f"Generando clubes de {country_name} (Liga {tier.value})",
                            done,
                            total_clubs,
                        )
                country.leagues.append(league)
            countries.append(country)

        return countries
