"""Entrenamiento por atributo: capacidad, curva (techos), asignacion y persistencia."""

import sqlite3

from tacticore import config
from tacticore.core.game import GameState
from tacticore.core.rng import new_rng
from tacticore.domain.employee import Employee
from tacticore.domain.enums import BonusType, EmployeeRole
from tacticore.domain.manager import Manager
from tacticore.generators import ClubGenerator, WorldGenerator
from tacticore.persistence import _db
from tacticore.simulation import training as tr


def _game(seed, monkeypatch):
    monkeypatch.setattr(config, "WORLD_COUNTRY_COUNT", 2)
    world = WorldGenerator(new_rng(seed)).generate()
    game = GameState.new(seed=seed, start_date=config.SEASON_START_DATE, countries=world)
    cc = world[0].code
    club = ClubGenerator(new_rng(seed)).player_club(
        name="C", fans_name="F", stadium_name="S",
        manager=Manager("A", "B", cc), country_code=cc,
        today=game.calendar.current_date)
    game.install_player_club(club)
    return game, club


def test_last_gains_recorded_and_reset_each_training(monkeypatch):
    game, club = _game(5, monkeypatch)
    # Todos entrenan Velocidad; los que mejoran quedan con last_gains['speed'].
    for p in club.players:
        tr.assign(p, "speed")
    tr.run_training(game, new_rng(1), game.calendar.current_date)
    improved = [p for p in club.players if p.last_gains]
    assert improved, "alguno deberia haber mejorado"
    for p in improved:
        assert set(p.last_gains) == {"speed"} and p.last_gains["speed"] > 0

    # Al siguiente entrenamiento (ahora Pase) las mejoras viejas se reinician.
    for p in club.players:
        tr.assign(p, "passing")
    tr.run_training(game, new_rng(2), game.calendar.current_date)
    for p in club.players:
        assert "speed" not in p.last_gains          # la mejora anterior se reseteo
        assert all(a == "passing" for a in p.last_gains)  # solo la de este entreno


def test_last_gains_not_persisted(monkeypatch):
    game, club = _game(5, monkeypatch)
    for p in club.players:
        tr.assign(p, "speed")
    tr.run_training(game, new_rng(1), game.calendar.current_date)
    assert any(p.last_gains for p in club.players)
    conn = sqlite3.connect(":memory:")
    _db.write_game(conn, game)
    g2 = _db.read_game(conn)
    # Es un realce transitorio: no viaja al save (queda vacio al cargar).
    assert all(not p.last_gains for p in g2.player_club.players)


def test_capacity_sums_coach_facility_and_staff(monkeypatch):
    game, club = _game(3, monkeypatch)
    base = tr.capacity(club)
    assert abs(base - club.coach.skill) < 0.01              # solo DT
    club.facilities["training"] = 3
    assert tr.capacity(club) > base                          # + centro de entrenamiento
    club.employees.append(Employee(role=EmployeeRole.DOCTOR, first_name="N", last_name="N",
        nationality="AR", birth_date=club.coach.birth_date,
        bonuses={BonusType.TRAINING: 100}, weekly_wage=1))
    assert tr.capacity(club) > club.coach.skill + 15         # + staff (con topes, <=100)
    assert tr.capacity(club) <= 100.0


def test_assign_is_exclusive(monkeypatch):
    game, club = _game(3, monkeypatch)
    p = club.players[0]
    tr.assign(p, "passing")
    assert p.training_focus == "passing"
    tr.assign(p, "shooting")                                 # cambia de foco (exclusivo)
    assert p.training_focus == "shooting"
    assert tr.group_for(club, "passing") == []
    tr.clear(p)
    assert p.training_focus is None


def test_training_raises_focused_attribute(monkeypatch):
    game, club = _game(3, monkeypatch)
    club.facilities["training"] = 3                          # sube la capacidad
    p = min(club.players, key=lambda pl: pl.age_on(game.calendar.current_date))
    p.passing = 20.0                                         # bien debajo del techo
    p.potential = 90.0
    tr.assign(p, "passing")
    before = p.passing
    rng = new_rng(1)
    for _ in range(10):                                     # varias semanas
        tr.run_training(game, rng, game.calendar.current_date)
    assert p.passing > before                               # subio con el entreno


def test_hard_cap_at_potential(monkeypatch):
    game, club = _game(3, monkeypatch)
    club.facilities["training"] = 3
    p = club.players[0]
    p.potential = 50.0
    p.passing = 49.9
    tr.assign(p, "passing")
    rng = new_rng(1)
    for _ in range(20):
        tr.run_training(game, rng, game.calendar.current_date)
    assert p.passing <= 50.0                                # nunca supera el potencial


def test_above_capacity_barely_trains(monkeypatch):
    game, club = _game(3, monkeypatch)                       # cap ~ coach skill (~30)
    cap = tr.capacity(club)
    p = club.players[0]
    p.potential = 99.0
    p.passing = cap + 25                                     # muy por encima del techo
    tr.assign(p, "passing")
    before = p.passing
    rng = new_rng(1)
    for _ in range(10):
        tr.run_training(game, rng, game.calendar.current_date)
    assert p.passing - before < 1.0                         # casi no sube


def test_bigger_group_trains_less_per_head(monkeypatch):
    game, club = _game(3, monkeypatch)
    club.facilities["training"] = 3
    today = game.calendar.current_date
    cap = tr.capacity(club)
    young = min(club.players, key=lambda p: p.age_on(today))
    small = tr.train_gain(young, "vision", cap, 1, today, new_rng(5))
    # reset y mismo jugador en grupo grande
    young.vision -= small
    big = tr.train_gain(young, "vision", cap, 9, today, new_rng(5))
    assert big <= small                                      # grupo grande: menos por cabeza


def test_run_training_notifies(monkeypatch):
    game, club = _game(3, monkeypatch)
    club.facilities["training"] = 3
    for p in club.players[:3]:
        tr.assign(p, "stamina")
    tr.run_training(game, new_rng(1), game.calendar.current_date)
    assert any(n.category == "entrenamiento" for n in game.notifications)


def test_round_trip_training_focus(monkeypatch):
    game, club = _game(3, monkeypatch)
    club.players[0].training_focus = "dribbling"
    club.players[1].training_focus = None
    conn = sqlite3.connect(":memory:")
    _db.write_game(conn, game)
    g2 = _db.read_game(conn)
    focuses = {p.training_focus for p in g2.player_club.players}
    assert "dribbling" in focuses
