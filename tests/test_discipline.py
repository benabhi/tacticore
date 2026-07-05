"""Disciplina: tarjetas, suspensiones y lesiones (disponibilidad + persistencia)."""

import sqlite3
from datetime import timedelta

from tacticore import config
from tacticore.core.game import GameState
from tacticore.core.rng import new_rng
from tacticore.domain.enums import InjurySeverity, InjuryType
from tacticore.domain.injury import Injury
from tacticore.domain.manager import Manager
from tacticore.generators import ClubGenerator, WorldGenerator
from tacticore.persistence import _db
from tacticore.simulation.auto_tactic import default_tactic
from tacticore.simulation.discipline import (
    generate_injury, recover_injuries, roll_match_events, serve_suspensions)
from tacticore.simulation.match.formation import (
    FORMATION_11, auto_select, pick_lineup)
from tacticore.simulation.season import ensure_all_fixtures


class _Rng:
    """rng de laboratorio: `random()` devuelve una secuencia fija; choice/randint
    deterministas (para forzar amarilla/roja sin depender de una semilla)."""

    def __init__(self, values):
        self.values = list(values)
        self.i = 0

    def random(self):
        v = self.values[self.i % len(self.values)]
        self.i += 1
        return v

    def choice(self, seq):
        return list(seq)[0]

    def randint(self, a, b):
        return a


def _game(seed, monkeypatch):
    monkeypatch.setattr(config, "WORLD_COUNTRY_COUNT", 3)
    world = WorldGenerator(new_rng(seed)).generate()
    game = GameState.new(seed=seed, start_date=config.SEASON_START_DATE, countries=world)
    cc = world[0].code
    club = ClubGenerator(new_rng(seed)).player_club(
        name="Mi Club", fans_name="F", stadium_name="S",
        manager=Manager("A", "B", cc), country_code=cc, today=game.calendar.current_date)
    game.install_player_club(club)
    ensure_all_fixtures(game)
    return game, club


def test_two_yellows_cause_one_match_suspension(monkeypatch):
    game, club = _game(11, monkeypatch)
    today = game.calendar.current_date
    p = club.players[0]
    # sin lesion (0.9) + valor en la banda amarilla (0.05)
    roll_match_events(game, club, [p], True, today, _Rng([0.9, 0.05]))
    assert p.yellow_cards == 1 and p.matches_suspended == 0
    roll_match_events(game, club, [p], True, today, _Rng([0.9, 0.05]))
    assert p.yellow_cards == 0 and p.matches_suspended == 1  # 2da amarilla -> ban


def test_red_card_suspends_and_friendly_has_no_cards(monkeypatch):
    game, club = _game(11, monkeypatch)
    today = game.calendar.current_date
    red = club.players[1]
    roll_match_events(game, club, [red], True, today, _Rng([0.9, 0.001]))  # r<roja
    assert red.matches_suspended == 1
    amistoso = club.players[2]
    roll_match_events(game, club, [amistoso], False, today, _Rng([0.9, 0.05]))
    assert amistoso.yellow_cards == 0  # en amistoso no hay tarjetas


def test_serve_suspensions_decrements(monkeypatch):
    game, club = _game(11, monkeypatch)
    club.players[0].matches_suspended = 2
    club.players[1].matches_suspended = 1
    serve_suspensions(club)
    assert club.players[0].matches_suspended == 1
    assert club.players[1].matches_suspended == 0


def test_injury_generation_and_recovery(monkeypatch):
    game, club = _game(11, monkeypatch)
    today = game.calendar.current_date
    injury, weeks = generate_injury(new_rng(5), today)
    assert 1 <= weeks <= 12
    assert injury.expected_return == today + timedelta(weeks=weeks)

    p = club.players[0]
    p.injury = Injury(InjuryType.KNEE, InjurySeverity.SEVERE, today,
                      today + timedelta(weeks=3))
    assert p.injury_weeks_left(today) == 3
    assert not p.is_available
    # avanza hasta el alta: recover la limpia
    recover_injuries(game, today + timedelta(weeks=3))
    assert p.injury is None and len(p.injury_history) == 1 and p.is_available


def test_unavailable_players_are_not_selected(monkeypatch):
    game, club = _game(11, monkeypatch)
    today = game.calendar.current_date
    injured, suspended = club.players[0], club.players[1]
    injured.injury = Injury(InjuryType.ANKLE, InjurySeverity.MINOR, today,
                            today + timedelta(weeks=2))
    suspended.matches_suspended = 1

    lineup = pick_lineup(club, FORMATION_11, available_only=True)
    assert injured not in lineup and suspended not in lineup
    xi, bench = auto_select(club, FORMATION_11, available_only=True)
    assert injured not in xi and injured not in bench
    assert suspended not in xi and suspended not in bench
    tactic = default_tactic(club, new_rng(1))
    assert injured not in tactic.lineup and suspended not in tactic.lineup


def test_round_trip_injury_and_cards(monkeypatch):
    game, club = _game(11, monkeypatch)
    today = game.calendar.current_date
    p = club.players[0]
    p.injury = Injury(InjuryType.HAMSTRING, InjurySeverity.MODERATE, today,
                      today + timedelta(weeks=4))
    p.yellow_cards = 1
    club.players[1].matches_suspended = 2

    conn = sqlite3.connect(":memory:")
    _db.write_game(conn, game)
    g2 = _db.read_game(conn)
    p2 = g2.player_club.players[0]
    assert p2.injury is not None
    assert p2.injury.type is InjuryType.HAMSTRING
    assert p2.injury.expected_return == today + timedelta(weeks=4)
    assert p2.yellow_cards == 1
    assert g2.player_club.players[1].matches_suspended == 2
