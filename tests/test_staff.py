"""Cuerpo de trabajo: bonus, sueldos, cupos, contratacion, efectos y persistencia."""

import sqlite3
from datetime import date, timedelta

from tacticore import config
from tacticore.core.game import GameState
from tacticore.core.rng import new_rng
from tacticore.domain.employee import Employee
from tacticore.domain.enums import BonusType as B, EmployeeRole, LeagueTier
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


def _emp(role, bonuses, tier=LeagueTier.E):
    """Empleado suelto para tests (bonuses = {BonusType: fuerza})."""
    power = sum(bonuses.values())
    return Employee(role=role, first_name="N", last_name="N", nationality="AR",
                    birth_date=date(1980, 1, 1), bonuses=dict(bonuses),
                    weekly_wage=staff.staff_wage(power, tier))


def test_wage_convex_in_power_and_grows_by_tier():
    w35 = staff.staff_wage(35, LeagueTier.E)
    w70 = staff.staff_wage(70, LeagueTier.E)
    w140 = staff.staff_wage(140, LeagueTier.E)
    assert w35 < w70 < w140                    # monotona en poder
    assert (w140 - w70) > (w70 - w35)          # convexa (acelera)
    assert (staff.staff_wage(100, LeagueTier.E)
            < staff.staff_wage(100, LeagueTier.C)
            < staff.staff_wage(100, LeagueTier.A))


def test_slots_from_base_plus_home_facility(monkeypatch):
    game, club = _game(11, monkeypatch)
    assert staff.staff_slots(club, EmployeeRole.DOCTOR) == 1     # base, sin enfermeria
    club.facilities["medical"] = 2                               # Enfermeria nivel 2
    assert staff.staff_slots(club, EmployeeRole.DOCTOR) == 3     # base + nivel
    club.facilities["oficina"] = 1
    assert staff.staff_slots(club, EmployeeRole.FINANCE) == 2


def test_slots_and_hire_fire(monkeypatch):
    game, club = _game(11, monkeypatch)
    doc = _emp(EmployeeRole.DOCTOR, {B.INJURY_PREVENT: 60})
    assert staff.hire(game, doc)
    assert not staff.can_hire(club, EmployeeRole.DOCTOR)             # cupo lleno en E
    assert not staff.hire(game, _emp(EmployeeRole.DOCTOR, {B.INJURY_PREVENT: 70}))
    staff.fire(game, doc)
    assert staff.can_hire(club, EmployeeRole.DOCTOR)                 # cupo liberado


def test_doctor_prevent_and_recover(monkeypatch):
    game, club = _game(11, monkeypatch)
    assert staff.injury_factor(club) == 1.0 and staff.injury_weeks_factor(club) == 1.0
    staff.hire(game, _emp(EmployeeRole.DOCTOR,
                          {B.INJURY_PREVENT: 100, B.INJURY_RECOVER: 100}))
    assert staff.injury_factor(club) < 1.0            # baja la probabilidad
    assert staff.injury_weeks_factor(club) < 1.0      # acorta la baja
    today = game.calendar.current_date
    _, weeks_full = generate_injury(new_rng(3), today, 1.0)
    _, weeks_cut = generate_injury(new_rng(3), today, 0.5)
    assert 1 <= weeks_cut <= weeks_full


def test_multiple_doctors_stack_prevention(monkeypatch):
    game, club = _game(11, monkeypatch)
    club.tier = LeagueTier.A
    club.facilities["medical"] = 3          # cupos para varios medicos
    staff.hire(game, _emp(EmployeeRole.DOCTOR, {B.INJURY_PREVENT: 80}, LeagueTier.A))
    f1 = staff.injury_factor(club)
    staff.hire(game, _emp(EmployeeRole.DOCTOR, {B.INJURY_PREVENT: 80}, LeagueTier.A))
    f2 = staff.injury_factor(club)
    assert 0.0 < f2 < f1 < 1.0


def test_finance_income_bonus_and_cap(monkeypatch):
    game, club = _game(11, monkeypatch)
    assert staff.income_bonus(club) == 0.0
    staff.hire(game, _emp(EmployeeRole.FINANCE, {B.INCOME: 100}))
    assert 0.0 < staff.income_bonus(club) <= 0.15
    club.tier = LeagueTier.A
    staff.hire(game, _emp(EmployeeRole.FINANCE, {B.INCOME: 100}, LeagueTier.A))
    assert staff.income_bonus(club) <= 0.15           # tope aun apilando


def test_new_live_bonuses_aggregate(monkeypatch):
    game, club = _game(11, monkeypatch)
    assert staff.gate_bonus(club) == 0 and staff.transfer_bonus(club) == 0
    assert staff.wage_reduction(club) == 0
    staff.hire(game, _emp(EmployeeRole.FINANCE,
                          {B.INCOME: 50, B.GATE: 80, B.TRANSFERS: 80, B.WAGES: 80}))
    assert staff.gate_bonus(club) > 0
    assert staff.transfer_bonus(club) > 0
    assert 0 < staff.wage_reduction(club) <= 0.10


def test_training_live_and_morale_inert(monkeypatch):
    game, club = _game(11, monkeypatch)
    staff.hire(game, _emp(EmployeeRole.DOCTOR,
                          {B.INJURY_PREVENT: 40, B.TRAINING: 90, B.MORALE: 90}))
    assert staff.is_live(B.TRAINING) and not staff.is_live(B.MORALE)   # TRAINING ya vive
    assert staff.training_bonus(club) > 0                              # aporta capacidad
    assert staff.income_bonus(club) == 0 and staff.gate_bonus(club) == 0  # moral no hace nada


def test_weekly_economy_uses_staff_bonuses(monkeypatch):
    game, club = _game(11, monkeypatch)
    staff.hire(game, _emp(EmployeeRole.FINANCE, {B.INCOME: 80, B.WAGES: 60}))
    friday = game.calendar.current_date
    while friday.weekday() != 4:
        friday += timedelta(days=1)
    club.movements.clear()
    daily._weekly_economy(game, friday, new_rng(1), None)
    concepts = {mv.concept: mv.amount for mv in club.movements}
    assert concepts["Empleados"] == -staff.staff_wage_bill(club)
    assert concepts["Gestion financiera"] > 0        # bonus de ingresos


def test_generated_employee_has_primary_and_1_to_3_bonuses():
    for role in (EmployeeRole.DOCTOR, EmployeeRole.FINANCE):
        e = EmployeeGenerator(new_rng(7)).generate(role, "AR", LeagueTier.C)
        assert staff.role_primary(role) in e.bonuses          # el primario del rol
        assert 1 <= len(e.bonuses) <= 3
        extras = set(e.bonuses) - {staff.role_primary(role)}
        assert extras <= set(staff.role_extras(role))         # extras de SU bolsa


def test_candidates_deterministic_and_varied():
    a = EmployeeGenerator(new_rng(7)).candidates(
        EmployeeRole.DOCTOR, LeagueTier.C, "AR", config.SEASON_START_DATE, n=3)
    b = EmployeeGenerator(new_rng(7)).candidates(
        EmployeeRole.DOCTOR, LeagueTier.C, "AR", config.SEASON_START_DATE, n=3)
    assert [e.power for e in a] == [e.power for e in b]        # determinista
    assert [e.weekly_wage for e in a] == [e.weekly_wage for e in b]
    assert len({round(e.power) for e in a}) > 1               # variados


def test_round_trip_employees(monkeypatch):
    game, club = _game(11, monkeypatch)
    staff.hire(game, _emp(EmployeeRole.DOCTOR,
                          {B.INJURY_PREVENT: 62.5, B.INJURY_RECOVER: 30.0}))
    staff.hire(game, _emp(EmployeeRole.FINANCE, {B.INCOME: 71.0}))
    conn = sqlite3.connect(":memory:")
    _db.write_game(conn, game)
    g2 = _db.read_game(conn)
    emps = g2.player_club.employees
    assert len(emps) == 2
    by_role = {e.role: e for e in emps}
    doc = by_role[EmployeeRole.DOCTOR]
    assert abs(doc.bonuses[B.INJURY_PREVENT] - 62.5) < 1e-6
    assert abs(doc.bonuses[B.INJURY_RECOVER] - 30.0) < 1e-6
    assert by_role[EmployeeRole.FINANCE].bonuses == {B.INCOME: 71.0}
