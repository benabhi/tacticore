"""Generador del mundo completo (paises -> ligas -> clubes -> jugadores).

Es el orquestador de los generadores chicos. Acepta un callback de progreso
para alimentar la pantalla de carga estilo Caves of Qud. Determinista por seed.
"""

import random
from collections.abc import Callable
from datetime import date

from .. import config
from ..domain.country import Country
from ..domain.enums import LeagueTier
from ..domain.league import League
from ..domain.positions import is_goalkeeper
from ..simulation.economy import asking_price
from .club_generator import ClubGenerator
from .data import country_data
from .name_generator import NameGenerator

# Probabilidad de que un club arranque con un jugador en venta (sembrar el mercado).
_LISTING_CHANCE = 0.30

# Firma del callback de progreso: (texto, hechos, total).
ProgressCallback = Callable[[str, int, int], None]


class WorldGenerator:
    """Genera el mundo entero a partir de una semilla."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()
        self._names = NameGenerator(self._rng)
        self._clubs = ClubGenerator(self._rng, self._names)

    def generate(
        self,
        progress: ProgressCallback | None = None,
        today: date | None = None,
    ) -> list[Country]:
        """Genera y devuelve la lista de paises con todo su contenido.

        Si se pasa `progress`, se lo llama tras cada club generado con un texto
        descriptivo, la cantidad hecha y el total (para la barra de carga).
        `today` (fecha de inicio de la partida) ancla las edades de los planteles.
        """
        today = today or config.SEASON_START_DATE
        # None = todos los paises; un numero = solo los primeros N (util en dev/tests).
        if config.WORLD_COUNTRY_COUNT is None:
            selected = country_data.COUNTRIES
        else:
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
                        today=today,
                    )
                    league.clubs.append(club)
                    done += 1
                    if progress is not None:
                        progress(f"Generando {country_name}...", done, total_clubs)
                self._seed_market(league, today)
                country.leagues.append(league)
            countries.append(country)

        return countries

    def _seed_market(self, league: League, today) -> None:
        """Algunos clubes de la liga ponen un jugador (excedente) en venta."""
        for club in league.clubs:
            if self._rng.random() >= _LISTING_CHANCE:
                continue
            outfield = [p for p in club.players if not is_goalkeeper(p.position)]
            if outfield:
                worst = min(outfield, key=lambda p: p.overall)
                worst.asking_price = asking_price(worst, today)
