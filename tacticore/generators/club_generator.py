"""Generador de clubes de fantasia (con su plantilla, estadio, DT y presidente)."""

import random
from datetime import date

from ..domain.club import Club
from ..domain.enums import LeagueTier, Position
from ..domain.president import President
from ..domain.stadium import Stadium
from .manager_generator import ManagerGenerator
from .name_generator import NameGenerator
from .player_generator import PlayerGenerator
from .president_generator import PresidentGenerator
from .stadium_generator import StadiumGenerator

# Capital inicial (en millones) y rango de asociados segun el nivel de la liga.
_TIER_CAPITAL: dict[LeagueTier, tuple[int, int]] = {
    LeagueTier.A: (20, 80),
    LeagueTier.B: (10, 40),
    LeagueTier.C: (5, 20),
    LeagueTier.D: (2, 10),
    LeagueTier.E: (1, 5),
}
_TIER_MEMBERS: dict[LeagueTier, tuple[int, int]] = {
    LeagueTier.A: (40_000, 120_000),
    LeagueTier.B: (20_000, 60_000),
    LeagueTier.C: (8_000, 30_000),
    LeagueTier.D: (3_000, 12_000),
    LeagueTier.E: (500, 5_000),
}

# Plan de plantilla (16): que posicion granular ocupa cada jugador generado.
# Cubre una 4-3-3 con suplentes (2 arqueros, central de sobra, ambos laterales,
# medios variados y los tres puestos de ataque). El orden no importa: se mezcla.
_SQUAD_PLAN: tuple[Position, ...] = (
    Position.GOALKEEPER, Position.GOALKEEPER,
    Position.CENTER_BACK, Position.CENTER_BACK, Position.CENTER_BACK,
    Position.LEFT_BACK, Position.RIGHT_BACK,
    Position.DEF_MID, Position.CENTER_MID, Position.CENTER_MID, Position.ATT_MID,
    Position.LEFT_MID, Position.RIGHT_MID,
    Position.LEFT_WING, Position.RIGHT_WING, Position.STRIKER,
)


def _short_name(name: str) -> str:
    """Sigla del club: iniciales/nucleo de cada palabra, hasta 5 letras."""
    return "".join(part[:3] for part in name.split()).upper()[:5]


class ClubGenerator:
    """Crea clubes con nombre, finanzas, estadio, hinchada, presidente, DT y plantilla."""

    def __init__(
        self,
        rng: random.Random | None = None,
        names: NameGenerator | None = None,
    ) -> None:
        self._rng = rng or random.Random()
        self._names = names or NameGenerator(self._rng)
        self._players = PlayerGenerator(self._rng, self._names)
        self._stadiums = StadiumGenerator(self._rng)
        self._managers = ManagerGenerator(self._rng, self._names)
        self._presidents = PresidentGenerator(self._rng, self._names)

    def generate(
        self,
        squad_size: int = 16,
        country_code: str = "FAN",
        tier: LeagueTier = LeagueTier.E,
        today: date | None = None,
    ) -> Club:
        """Genera un club IA de la liga `tier` en el pais `country_code`.

        La plantilla respeta los minimos por posicion (`_SQUAD_MINIMUMS`) mas
        comodines hasta `squad_size`. `today` (fecha del juego) ancla las edades.
        """
        name = self._names.club_name()
        players = self._build_squad(squad_size, tier, country_code, today, name)
        capital = self._rng.randint(*_TIER_CAPITAL[tier]) * 1_000_000
        members = self._rng.randint(*_TIER_MEMBERS[tier])

        return Club(
            name=name,
            short_name=_short_name(name),
            country_code=country_code,
            tier=tier,
            stadium=self._stadiums.generate(tier, name),
            capital=capital,
            members=members,
            fans_name=self._names.fan_group_name(),
            president=self._presidents.generate(country_code, today),
            manager=self._managers.generate(country_code, today),
            players=players,
        )

    def player_club(
        self,
        name: str,
        fans_name: str,
        stadium_name: str,
        president: President,
        country_code: str,
        squad_size: int = 16,
        tier: LeagueTier = LeagueTier.E,
        members: int = 500,
        today: date | None = None,
    ) -> Club:
        """Construye el club humilde del jugador con la identidad que eligio.

        El nombre, la hinchada, el estadio y el presidente vienen del jugador; el
        DT y la plantilla (en `tier`) se generan. Arranca con pocos socios y el
        capital minimo de su nivel.
        """
        players = self._build_squad(squad_size, tier, country_code, today, name)
        capacity = self._rng.randint(*self._stadiums.capacity_range(tier))
        capital = _TIER_CAPITAL[tier][0] * 1_000_000

        return Club(
            name=name,
            short_name=_short_name(name),
            country_code=country_code,
            tier=tier,
            stadium=Stadium(name=stadium_name, capacity=capacity),
            capital=capital,
            members=members,
            fans_name=fans_name,
            president=president,
            manager=self._managers.generate(country_code, today),
            players=players,
        )

    def _build_squad(
        self,
        squad_size: int,
        tier: LeagueTier,
        country_code: str,
        today: date | None,
        club_name: str,
    ) -> list:
        """Arma la plantilla segun `_SQUAD_PLAN` (posicion por jugador), con dorsales."""
        positions = list(_SQUAD_PLAN)
        if squad_size <= len(positions):
            positions = positions[:squad_size]
        else:
            # Comodines extra: posiciones de campo al azar (nunca arquero).
            outfield = [p for p in _SQUAD_PLAN if p is not Position.GOALKEEPER]
            positions += [
                self._rng.choice(outfield) for _ in range(squad_size - len(positions))
            ]
        players = [
            self._players.generate(pos, tier, country_code, today) for pos in positions
        ]
        # Mezclar para que las posiciones no queden agrupadas al asignar dorsales.
        self._rng.shuffle(players)
        for number, player in enumerate(players, start=1):
            player.shirt_number = number
            player.origin_club = club_name
        return players
