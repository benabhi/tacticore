"""Cuerpo de trabajo: sueldos, cupos, contratacion, efectos y persistencia."""

import sqlite3
from datetime import date, timedelta

from tacticore import config
from tacticore.core.game import GameState
from tacticore.core.rng import new_rng
from tacticore.domain.enums import EmployeeRole, LeagueTier
from tacticore.domain.manager import Manager
from tacticore.generators import ClubGenerator, EmployeeGenerator, WorldGenerator
from tacticore.persistence import _db
from tacticore.simulation import daily, staff
from tacticore.simulation.discipline import generate_injury


def _game(seed, monkeypatch):
    monkeypatch.setattr(config, "WORLD_COUNTRY_COUNT", 3)
    world = WorldGenerator(new_rng(seed)).generate()
    game = GameState.new(seed=seed, start_date=config.SEASON_START_DATE, countries=world)
    cc = world[0].code
    club = ClubGenerator(new_rng(seed)).player_club(
        name="Mi Club", fans_name="F", stadium_name="S",
        manager=Manager("A", "B", cc), country_code=cc,
        today=game.calendar.current_date)
    game.install_player_club(club)
    return game, club


def _emp(role, skill, tier=LeagueTier.E):
    """Empleado suelto para tests (sin generador)."""
    from tacticore.domain.employee import Employee
    return Employee(role=role, first_name="N", last_name="N", nationality="AR",
                    birth_date=date(1980, 1, 1), skill=skill,
                    weekly_wage=staff.staff_wage(role, skill, tier))


def test_wage_convex_in_skill_and_grows_by_tier():
    d = EmployeeRole.DOCTOR
    w35 = staff.staff_wage(d, 35, LeagueTier.E)
    w50 = staff.staff_wage(d, 50, LeagueTier.E)
    w80 = staff.staff_wage(d, 80, LeagueTier.E)
    assert w35 < w50 < w80                    # monotona en skill
    assert (w80 - w50) > (w50 - w35)          # convexa (acelera)
    # crece por tier
    assert (staff.staff_wage(d, 80, LeagueTier.E)
            < staff.staff_wage(d, 80, LeagueTier.C)
            < staff.staff_wage(d, 80, LeagueTier.A))


def test_slots_and_hire_fire(monkeypatch):
    game, club = _game(11, monkeypatch)
    assert staff.staff_slots(EmployeeRole.DOCTOR, LeagueTier.E) == 1
    assert staff.staff_slots(EmployeeRole.DOCTOR, LeagueTier.A) == 3
    assert staff.can_hire(club, EmployeeRole.DOCTOR)
    doc = _emp(EmployeeRole.DOCTOR, 60)
    assert staff.hire(game, doc)
    assert staff.role_count(club, EmployeeRole.DOCTOR) == 1
    assert not staff.can_hire(club, EmployeeRole.DOCTOR)  # cupo lleno en E
    assert not staff.hire(game, _emp(EmployeeRole.DOCTOR, 70))  # no supera el tope
    staff.fire(game, doc)
    assert staff.role_count(club, EmployeeRole.DOCTOR) == 0
    assert staff.can_hire(club, EmployeeRole.DOCTOR)          # cupo liberado


def test_multiple_doctors_stack_in_high_tier(monkeypatch):
    game, club = _game(11, monkeypatch)
    club.tier = LeagueTier.A  # 3 cupos por rol
    assert staff.hire(game, _emp(EmployeeRole.DOCTOR, 80, LeagueTier.A))
    f1 = staff.injury_factor(club)
    assert staff.hire(game, _emp(EmployeeRole.DOCTOR, 80, LeagueTier.A))
    f2 = staff.injury_factor(club)
    assert f2 < f1 < 1.0             # apilar reduce mas, pero acotado (>0)
    assert f2 > 0.0


def test_doctor_reduces_injury_risk_and_shortens(monkeypatch):
    game, club = _game(11, monkeypatch)
    assert staff.injury_factor(club) == 1.0            # sin medico, sin efecto
    assert staff.injury_weeks_factor(club) == 1.0
    staff.hire(game, _emp(EmployeeRole.DOCTOR, 100))
    assert staff.injury_factor(club) < 1.0             # baja la probabilidad
    assert staff.injury_weeks_factor(club) < 1.0       # acorta la baja
    # generate_injury respeta el factor de semanas
    today = game.calendar.current_date
    long_inj, weeks_full = generate_injury(new_rng(3), today, 1.0)
    short_inj, weeks_cut = generate_injury(new_rng(3), today, 0.5)
    assert weeks_cut <= weeks_full
    assert weeks_cut >= 1


def test_finance_director_bonus_and_cap(monkeypatch):
    game, club = _game(11, monkeypatch)
    assert staff.finance_income_bonus(club) == 0.0
    staff.hire(game, _emp(EmployeeRole.FINANCE, 100))
    bonus = staff.finance_income_bonus(club)
    assert 0.0 < bonus <= 0.15
    # apilar (en tier alto) suma con rendimiento decreciente, sin pasar el tope
    club.tier = LeagueTier.A
    staff.hire(game, _emp(EmployeeRole.FINANCE, 100, LeagueTier.A))
    assert staff.finance_income_bonus(club) <= 0.15


def test_weekly_economy_deducts_staff_and_adds_bonus(monkeypatch):
    game, club = _game(11, monkeypatch)
    staff.hire(game, _emp(EmployeeRole.DOCTOR, 60))
    staff.hire(game, _emp(EmployeeRole.FINANCE, 80))
    friday = game.calendar.current_date
    while friday.weekday() != 4:
        friday += timedelta(days=1)
    club.movements.clear()
    daily._weekly_economy(game, friday, new_rng(1), None)
    concepts = {mv.concept: mv.amount for mv in club.movements}
    assert concepts["Empleados"] == -staff.staff_wage_bill(club)
    assert concepts["Gestion financiera"] > 0


def test_candidates_are_deterministic_and_varied():
    a = EmployeeGenerator(new_rng(7)).candidates(
        EmployeeRole.DOCTOR, LeagueTier.C, "AR", config.SEASON_START_DATE, n=3)
    b = EmployeeGenerator(new_rng(7)).candidates(
        EmployeeRole.DOCTOR, LeagueTier.C, "AR", config.SEASON_START_DATE, n=3)
    assert [e.skill for e in a] == [e.skill for e in b]       # determinista
    assert [e.weekly_wage for e in a] == [e.weekly_wage for e in b]
    assert len({round(e.skill) for e in a}) > 1               # variados


def test_round_trip_employees(monkeypatch):
    game, club = _game(11, monkeypatch)
    staff.hire(game, _emp(EmployeeRole.DOCTOR, 62.5))
    staff.hire(game, _emp(EmployeeRole.FINANCE, 71.0))
    conn = sqlite3.connect(":memory:")
    _db.write_game(conn, game)
    g2 = _db.read_game(conn)
    emps = g2.player_club.employees
    assert len(emps) == 2
    by_role = {e.role: e for e in emps}
    assert abs(by_role[EmployeeRole.DOCTOR].skill - 62.5) < 1e-6
    assert by_role[EmployeeRole.FINANCE].weekly_wage == staff.staff_wage(
        EmployeeRole.FINANCE, 71.0, LeagueTier.E)
