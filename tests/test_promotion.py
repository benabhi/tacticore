"""Fin de temporada: ascensos/descensos, fixture nuevo y persistencia."""

import sqlite3

from tacticore import config
from tacticore.core.game import GameState
from tacticore.core.rng import new_rng
from tacticore.domain.enums import LeagueTier, MatchKind
from tacticore.domain.manager import Manager
from tacticore.generators import ClubGenerator, WorldGenerator
from tacticore.persistence import _db
from tacticore.simulation import promotion
from tacticore.simulation.match_engine import simulate_match
from tacticore.simulation.season import (
    compute_standings, ensure_all_fixtures, ensure_player_friendlies)

_TIER_ORDER = list(LeagueTier)  # [A, B, C, D, E]


def _game(seed, monkeypatch, countries=2):
    monkeypatch.setattr(config, "WORLD_COUNTRY_COUNT", countries)
    world = WorldGenerator(new_rng(seed)).generate()
    game = GameState.new(seed=seed, start_date=config.SEASON_START_DATE, countries=world)
    cc = world[0].code
    club = ClubGenerator(new_rng(seed)).player_club(
        name="Mi Club", fans_name="F", stadium_name="S",
        manager=Manager("A", "B", cc), country_code=cc,
        today=game.calendar.current_date)
    game.install_player_club(club)
    ensure_all_fixtures(game)
    ensure_player_friendlies(game)
    return game, club


def _play_all_leagues(game, rng):
    """Juega TODOS los partidos de liga (deja la temporada terminada)."""
    for co in game.countries:
        for lg in co.leagues:
            for m in lg.matches:
                res = simulate_match(m.home, m.away, rng)
                m.home_goals, m.away_goals, m.played = res.home_goals, res.away_goals, True


def _sorted_leagues(country):
    return sorted(country.leagues, key=lambda lg: _TIER_ORDER.index(lg.tier))


def test_season_over_detection(monkeypatch):
    game, _ = _game(11, monkeypatch)
    assert not promotion.season_over(game)          # nada jugado
    _play_all_leagues(game, new_rng(1))
    assert promotion.season_over(game)              # todo jugado


def test_top_and_bottom_swap_between_divisions(monkeypatch):
    game, _ = _game(11, monkeypatch)
    _play_all_leagues(game, new_rng(1))
    co = game.countries[0]
    leagues = _sorted_leagues(co)
    # Capturar top-2 y bottom-2 de cada liga ANTES de mover.
    expect = {}
    for i in range(len(leagues) - 1):
        upper, lower = leagues[i], leagues[i + 1]
        expect[(i, "releg")] = [s.club for s in compute_standings(upper)[-2:]]
        expect[(i, "promo")] = [s.club for s in compute_standings(lower)[:2]]

    promotion.run_season_transition(game, new_rng(2))

    for i in range(len(leagues) - 1):
        upper, lower = leagues[i], leagues[i + 1]
        for c in expect[(i, "releg")]:              # bajaron a la liga de abajo
            assert c.tier is lower.tier and c in lower.clubs
        for c in expect[(i, "promo")]:              # subieron a la liga de arriba
            assert c.tier is upper.tier and c in upper.clubs
    assert game.season == 2


def test_league_sizes_and_no_clubs_lost(monkeypatch):
    game, _ = _game(11, monkeypatch)
    before = {id(c) for co in game.countries for lg in co.leagues for c in lg.clubs}
    _play_all_leagues(game, new_rng(1))
    promotion.run_season_transition(game, new_rng(2))
    after = {id(c) for co in game.countries for lg in co.leagues for c in lg.clubs}
    assert before == after                          # ni se pierden ni se duplican
    for co in game.countries:
        for lg in co.leagues:
            assert len(lg.clubs) == 8               # cada liga sigue con 8
            for c in lg.clubs:
                assert c.tier is lg.tier            # tier coherente con la liga


def test_new_fixture_generated_after_transition(monkeypatch):
    game, _ = _game(11, monkeypatch)
    last_old = max(m.match_date for lg in game.countries[0].leagues for m in lg.matches)
    _play_all_leagues(game, new_rng(1))
    # La transicion usa la fecha del juego; en el juego real cae al final de la
    # temporada, asi que le pasamos la fecha de la ultima jornada.
    promotion.run_season_transition(game, new_rng(2), today=last_old)
    pl = game.player_league
    league_matches = [m for m in pl.matches if m.kind is MatchKind.LEAGUE]
    assert league_matches and all(not m.played for m in league_matches)   # todo por jugar
    assert min(m.match_date for m in league_matches) > last_old           # tras el receso
    assert game.friendlies and all(not f.played for f in game.friendlies)


def test_player_promoted_when_finishing_top(monkeypatch):
    game, club = _game(11, monkeypatch)
    _play_all_leagues(game, new_rng(1))
    pl = compute_standings(game.player_league)
    pos = next(i for i, s in enumerate(pl, 1) if s.club is club)
    old_tier = club.tier
    promotion.run_season_transition(game, new_rng(2))
    if pos <= promotion._PROMOTE_COUNT:             # salio top-2 -> asciende
        assert _TIER_ORDER.index(club.tier) < _TIER_ORDER.index(old_tier)


def test_transition_is_deterministic(monkeypatch):
    g1, _ = _game(11, monkeypatch)
    _play_all_leagues(g1, new_rng(1))
    promotion.run_season_transition(g1, new_rng(2))
    g2, _ = _game(11, monkeypatch)
    _play_all_leagues(g2, new_rng(1))
    promotion.run_season_transition(g2, new_rng(2))
    a = sorted(c.name for c in g1.countries[0].leagues[0].clubs)
    b = sorted(c.name for c in g2.countries[0].leagues[0].clubs)
    assert a == b


def test_round_trip_season_and_tiers(monkeypatch):
    game, club = _game(11, monkeypatch)
    _play_all_leagues(game, new_rng(1))
    promotion.run_season_transition(game, new_rng(2))
    conn = sqlite3.connect(":memory:")
    _db.write_game(conn, game)
    g2 = _db.read_game(conn)
    assert g2.season == 2
    assert g2.player_club.tier is club.tier
    # cada club sigue con el tier de su liga tras el round-trip
    for co in g2.countries:
        for lg in co.leagues:
            for c in lg.clubs:
                assert c.tier is lg.tier
