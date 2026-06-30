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

from ..domain.club import Club
from ..domain.league import League
from ..domain.match import Match

# Puntos por resultado (3-1-0, estandar moderno).
_WIN_POINTS = 3
_DRAW_POINTS = 1


def build_fixture(clubs: list[Club], rng: random.Random) -> list[Match]:
    """Arma el fixture de ida y vuelta de `clubs` (round-robin doble).

    Devuelve todos los partidos con su numero de jornada (1..2*(N-1)). El orden
    de los equipos se mezcla con `rng` para que cada liga tenga su propio
    calendario (determinista por semilla).
    """
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
            matches.append(Match(home=home, away=away, matchday=r + 1))
            matches.append(
                Match(home=away, away=home, matchday=r + 1 + rounds_per_leg)
            )
        # Rotacion del circulo: se fija order[0] y rota el resto.
        order = [order[0]] + [order[-1]] + order[1:-1]

    matches.sort(key=lambda m: m.matchday)
    return matches


def generate_league_fixture(league: League, rng: random.Random) -> None:
    """Genera (in-place) el fixture de la temporada de `league` si no lo tiene."""
    if league.matches:
        return
    league.matches = build_fixture(league.clubs, rng)


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


def compute_standings(league: League) -> list[Standing]:
    """Tabla de posiciones derivada de los partidos jugados de la liga.

    Ordena por puntos, luego diferencia de gol, goles a favor y nombre. La
    `form` de cada club son sus resultados en orden de jornada (para mostrar los
    ultimos N). Al inicio de temporada (nada jugado) todo queda en cero.
    """
    # Club es un dataclass mutable (no hasheable): se indexa por id() del objeto.
    table = {id(club): Standing(club) for club in league.clubs}
    # Resultados por club ordenables por jornada, para derivar la forma reciente.
    history: dict[int, list[tuple[int, str]]] = {id(club): [] for club in league.clubs}

    for m in league.matches:
        if not m.played:
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
