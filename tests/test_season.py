"""Tests del fixture de liga (round-robin doble) y la tabla de posiciones."""

from collections import Counter
from datetime import timedelta

from tacticore.core.rng import new_rng
from tacticore.domain.enums import LeagueTier
from tacticore.domain.league import League
from tacticore.generators import ClubGenerator
from tacticore.simulation.season import (
    build_fixture,
    compute_standings,
    generate_league_fixture,
)


def _league(seed: int = 1, n: int = 8) -> League:
    gen = ClubGenerator(new_rng(seed))
    clubs = [gen.generate(squad_size=16, tier=LeagueTier.E) for _ in range(n)]
    return League(name="Liga Test", tier=LeagueTier.E, country_code="AR", clubs=clubs)


def test_fixture_is_double_round_robin():
    league = _league()
    clubs = league.clubs
    n = len(clubs)
    matches = build_fixture(clubs, new_rng(5))

    # N*(N-1) partidos: cada par juega dos veces.
    assert len(matches) == n * (n - 1)
    # Cada par ordenado (local, visitante) aparece exactamente una vez.
    pairs = Counter((m.home.name, m.away.name) for m in matches)
    assert all(count == 1 for count in pairs.values())
    # Cada par NO ordenado se enfrenta exactamente dos veces (ida y vuelta).
    unordered = Counter(frozenset((m.home.name, m.away.name)) for m in matches)
    assert all(count == 2 for count in unordered.values())
    # Nadie juega contra si mismo.
    assert all(m.home is not m.away for m in matches)


def test_fixture_balances_home_and_away():
    league = _league()
    n = len(league.clubs)
    matches = build_fixture(league.clubs, new_rng(7))
    home = Counter(m.home.name for m in matches)
    away = Counter(m.away.name for m in matches)
    # Cada equipo juega N-1 de local y N-1 de visitante.
    for club in league.clubs:
        assert home[club.name] == n - 1
        assert away[club.name] == n - 1


def test_fixture_no_team_plays_twice_per_matchday():
    league = _league()
    matches = build_fixture(league.clubs, new_rng(3))
    by_round: dict[int, list] = {}
    for m in matches:
        by_round.setdefault(m.matchday, []).extend([m.home.name, m.away.name])
    rounds = max(by_round)
    assert rounds == 2 * (len(league.clubs) - 1)
    for teams in by_round.values():
        assert len(teams) == len(set(teams))  # sin repetidos en la jornada


def test_fixture_is_deterministic():
    league = _league()
    a = build_fixture(league.clubs, new_rng(9))
    b = build_fixture(league.clubs, new_rng(9))
    assert [(m.home.name, m.away.name, m.matchday) for m in a] == \
           [(m.home.name, m.away.name, m.matchday) for m in b]


def test_fixture_dates_are_weekly_saturdays():
    from datetime import date

    league = _league()
    matches = build_fixture(league.clubs, new_rng(5), start_date=date(2025, 7, 1))
    by_round = {}
    for m in matches:
        assert m.match_date is not None
        assert m.match_date.weekday() == 5  # sabado
        by_round.setdefault(m.matchday, m.match_date)
    # Jornadas consecutivas: una semana de diferencia.
    assert by_round[2] - by_round[1] == timedelta(days=7)


def test_standings_empty_at_season_start():
    league = _league()
    generate_league_fixture(league, new_rng(2))
    table = compute_standings(league)
    assert len(table) == len(league.clubs)
    assert all(s.played == 0 and s.points == 0 for s in table)
    assert all(s.form == [] for s in table)


def test_standings_count_points_and_order():
    league = _league()
    generate_league_fixture(league, new_rng(2))
    a, b, c = league.clubs[0], league.clubs[1], league.clubs[2]

    def play(home, away, hg, ag):
        for m in league.matches:
            if m.home is home and m.away is away and not m.played:
                m.home_goals, m.away_goals, m.played = hg, ag, True
                return
        raise AssertionError("no encontre ese partido en el fixture")

    play(a, b, 3, 0)   # a gana
    play(c, a, 1, 1)   # empatan
    table = {id(s.club): s for s in compute_standings(league)}
    assert table[id(a)].points == 4 and table[id(a)].won == 1 and table[id(a)].drawn == 1
    assert table[id(a)].goals_for == 4 and table[id(a)].goals_against == 1
    assert table[id(b)].points == 0 and table[id(b)].lost == 1
    assert table[id(c)].points == 1
    # 'a' va primero (mas puntos).
    assert compute_standings(league)[0].club is a
    assert compute_standings(league)[0].form == ["G", "E"]
