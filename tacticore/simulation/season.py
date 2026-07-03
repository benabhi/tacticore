"""Temporada de liga: fixture (todos contra todos) y tabla de posiciones.

El fixture es un round-robin DOBLE (ida y vuelta): cada equipo juega contra todos
una vez de local y una de visitante. Se arma con el "metodo del circulo" (tablas
de Berger): se fija un equipo y se rotan los demas cada jornada; la vuelta repite
la ida invirtiendo localia, lo que garantiza el balance local/visitante.

La tabla de posiciones se DERIVA de los partidos jugados (no se guarda aparte):
se recorre el fixture y se cuentan puntos, goles y forma reciente.
"""

import random
from dataclasses import dataclass, field
from datetime import date, timedelta

from .. import config
from ..domain.club import Club
from ..domain.league import League
from ..domain.match import Match

# Puntos por resultado (3-1-0, estandar moderno).
_WIN_POINTS = 3
_DRAW_POINTS = 1


def _matchday_date(start_date: date, matchday: int) -> date:
    """Fecha de una jornada: se juega los sabados, una jornada por semana."""
    days_to_saturday = (5 - start_date.weekday()) % 7  # 5 = sabado
    first = start_date + timedelta(days=days_to_saturday or 7)  # el proximo sabado
    return first + timedelta(weeks=matchday - 1)


def build_fixture(
    clubs: list[Club], rng: random.Random, start_date: date | None = None
) -> list[Match]:
    """Arma el fixture de ida y vuelta de `clubs` (round-robin doble).

    Devuelve todos los partidos con su numero de jornada (1..2*(N-1)) y su fecha
    (una jornada por semana, los sabados, desde `start_date`). El orden de los
    equipos se mezcla con `rng` para que cada liga tenga su propio calendario
    (determinista por semilla).
    """
    start_date = start_date or config.SEASON_START_DATE
    teams: list[Club | None] = list(clubs)
    rng.shuffle(teams)
    # Con un numero impar de equipos, uno descansa cada jornada (BYE = None).
    if len(teams) % 2 == 1:
        teams.append(None)

    n = len(teams)
    half = n // 2
    rounds_per_leg = n - 1
    order = list(teams)
    matches: list[Match] = []

    for r in range(rounds_per_leg):
        for i in range(half):
            a, b = order[i], order[n - 1 - i]
            if a is None or b is None:
                continue  # el que enfrenta al BYE descansa esa jornada
            # Alternar localia dentro de la ida para repartir locales/visitantes;
            # la vuelta (mas abajo) invierte, asi el balance global queda perfecto.
            if (r + i) % 2 == 0:
                home, away = a, b
            else:
                home, away = b, a
            # Ida en la jornada r+1; vuelta en la jornada r+1+rounds_per_leg.
            md_ida = r + 1
            md_vuelta = r + 1 + rounds_per_leg
            matches.append(Match(
                home=home, away=away, matchday=md_ida,
                match_date=_matchday_date(start_date, md_ida),
            ))
            matches.append(Match(
                home=away, away=home, matchday=md_vuelta,
                match_date=_matchday_date(start_date, md_vuelta),
            ))
        # Rotacion del circulo: se fija order[0] y rota el resto.
        order = [order[0]] + [order[-1]] + order[1:-1]

    matches.sort(key=lambda m: m.matchday)
    return matches


def generate_league_fixture(
    league: League, rng: random.Random, start_date: date | None = None
) -> None:
    """Genera (in-place) el fixture de la temporada de `league` si no lo tiene."""
    if league.matches:
        return
    league.matches = build_fixture(league.clubs, rng, start_date)


def ensure_all_fixtures(game, start_date: date | None = None) -> None:
    """Genera el fixture de CADA liga del mundo que aun no lo tenga.

    Necesario para que el loop diario haga progresar todas las ligas (no solo la
    del jugador). Cada liga usa una semilla propia (derivada de la del juego) para
    ser determinista. Idempotente: las ligas que ya tienen fixture se saltean.
    """
    from ..core.rng import new_rng

    index = 0
    for country in game.countries:
        for league in country.leagues:
            generate_league_fixture(league, new_rng(game.seed + index), start_date)
            index += 1


@dataclass
class Standing:
    """Fila de la tabla de posiciones de un club."""

    club: Club
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0
    form: list[str] = field(default_factory=list)  # ultimos resultados: G/E/P

    @property
    def points(self) -> int:
        return self.won * _WIN_POINTS + self.drawn * _DRAW_POINTS

    @property
    def goal_diff(self) -> int:
        return self.goals_for - self.goals_against


def compute_standings(league: League, upto_matchday: int | None = None) -> list[Standing]:
    """Tabla de posiciones derivada de los partidos jugados de la liga.

    Ordena por puntos, luego diferencia de gol, goles a favor y nombre. La
    `form` de cada club son sus resultados en orden de jornada (para mostrar los
    ultimos N). Al inicio de temporada (nada jugado) todo queda en cero.

    Si se pasa `upto_matchday`, solo cuenta los partidos hasta esa jornada
    (inclusive): sirve para reconstruir la tabla de una jornada anterior y
    comparar posiciones (columna de movimiento).
    """
    # Club es un dataclass mutable (no hasheable): se indexa por id() del objeto.
    table = {id(club): Standing(club) for club in league.clubs}
    # Resultados por club ordenables por jornada, para derivar la forma reciente.
    history: dict[int, list[tuple[int, str]]] = {id(club): [] for club in league.clubs}

    for m in league.matches:
        if not m.played:
            continue
        if upto_matchday is not None and m.matchday > upto_matchday:
            continue
        home, away = table[id(m.home)], table[id(m.away)]
        home.played += 1
        away.played += 1
        home.goals_for += m.home_goals
        home.goals_against += m.away_goals
        away.goals_for += m.away_goals
        away.goals_against += m.home_goals
        if m.home_goals > m.away_goals:
            home.won += 1
            away.lost += 1
            history[id(m.home)].append((m.matchday, "G"))
            history[id(m.away)].append((m.matchday, "P"))
        elif m.home_goals < m.away_goals:
            away.won += 1
            home.lost += 1
            history[id(m.home)].append((m.matchday, "P"))
            history[id(m.away)].append((m.matchday, "G"))
        else:
            home.drawn += 1
            away.drawn += 1
            history[id(m.home)].append((m.matchday, "E"))
            history[id(m.away)].append((m.matchday, "E"))

    for club_id, standing in table.items():
        standing.form = [result for _, result in sorted(history[club_id])]

    return sorted(
        table.values(),
        key=lambda s: (-s.points, -s.goal_diff, -s.goals_for, s.club.name),
    )
