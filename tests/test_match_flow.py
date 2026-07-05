"""Flujo del partido del club del jugador: tactica automatica, saltar el partido
en el loop diario y cerrarlo con el resultado del motor en vivo."""

from datetime import timedelta

from tacticore import config
from tacticore.core.game import GameState
from tacticore.core.rng import new_rng
from tacticore.domain.enums import Mentality
from tacticore.domain.manager import Manager
from tacticore.generators import ClubGenerator, WorldGenerator
from tacticore.simulation.auto_tactic import _category_formations, default_tactic
from tacticore.simulation.daily import (
    advance_day, finish_player_match, player_match_on)
from tacticore.simulation.formation_training import offensiveness
from tacticore.simulation.season import ensure_all_fixtures


def _game(seed: int, monkeypatch, mentality=Mentality.NEUTRAL):
    monkeypatch.setattr(config, "WORLD_COUNTRY_COUNT", 3)
    world = WorldGenerator(new_rng(seed)).generate()
    game = GameState.new(seed=seed, start_date=config.SEASON_START_DATE, countries=world)
    cc = world[0].code
    club = ClubGenerator(new_rng(seed)).player_club(
        name="Mi Club", fans_name="F", stadium_name="Estadio S",
        manager=Manager("A", "B", cc), country_code=cc,
        coach_mentality=mentality, today=game.calendar.current_date,
    )
    game.install_player_club(club)
    ensure_all_fixtures(game)
    return game, club


def test_default_tactic_formation_matches_coach_mentality(monkeypatch):
    """Un DT ofensivo sale con formacion ofensiva; uno defensivo, defensiva."""
    for mentality in Mentality:
        game, club = _game(3, monkeypatch, mentality)
        tactic = default_tactic(club, new_rng(1))
        assert tactic.formation in _category_formations(mentality)
        # la alineacion queda completa (11 titulares, sin huecos)
        assert tactic.lineup and all(p is not None for p in tactic.lineup)
    # coherencia de la clasificacion: ofensiva > defensiva
    game, club = _game(3, monkeypatch, Mentality.OFFENSIVE)
    off = default_tactic(club, new_rng(1)).formation
    game, club = _game(3, monkeypatch, Mentality.DEFENSIVE)
    dfn = default_tactic(club, new_rng(1)).formation
    assert offensiveness(off) > offensiveness(dfn)


def _next_player_match(game, club):
    league = game.player_league
    upcoming = [m for m in league.matches
                if (m.home is club or m.away is club) and not m.played]
    return min(upcoming, key=lambda m: m.matchday)


def test_skip_player_match_leaves_it_pending(monkeypatch):
    """Con skip_player_match, el partido del jugador queda sin jugar pero el resto
    de la liga si se resuelve ese dia."""
    game, club = _game(11, monkeypatch)
    target = _next_player_match(game, club).match_date
    while game.calendar.current_date < target:
        advance_day(game, skip_player_match=True)
    match = player_match_on(game, target)
    assert match is not None and not match.played
    league = game.player_league
    others = [m for m in league.matches if m.match_date == target and m is not match]
    assert others and all(m.played for m in others)


def test_finish_player_match_records_result(monkeypatch):
    """finish_player_match anota el marcador del motor en vivo y da taquilla."""
    game, club = _game(11, monkeypatch)
    target = _next_player_match(game, club).match_date
    while game.calendar.current_date < target:
        advance_day(game, skip_player_match=True)
    match = player_match_on(game, target)
    cap_before = match.home.capital
    finish_player_match(game, match, 2, 1)
    assert match.played and (match.home_goals, match.away_goals) == (2, 1)
    assert match.home.capital > cap_before  # el local cobra la taquilla
