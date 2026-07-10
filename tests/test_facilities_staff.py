"""Construcciones <-> staff: cupos por instalacion y efectos (lesiones/entreno/ingresos)."""

from tacticore import config
from tacticore.core.game import GameState
from tacticore.core.rng import new_rng
from tacticore.domain.enums import EmployeeRole, LeagueTier
from tacticore.domain.manager import Manager
from tacticore.generators import ClubGenerator, WorldGenerator
from tacticore.simulation import facilities as fac
from tacticore.simulation import staff
from tacticore.simulation.formation_training import train_formation


def _game(seed, monkeypatch):
    monkeypatch.setattr(config, "WORLD_COUNTRY_COUNT", 2)
    world = WorldGenerator(new_rng(seed)).generate()
    game = GameState.new(seed=seed, start_date=config.SEASON_START_DATE, countries=world)
    cc = world[0].code
    club = ClubGenerator(new_rng(seed)).player_club(
        name="Mi Club", fans_name="F", stadium_name="S",
        manager=Manager("A", "B", cc), country_code=cc,
        today=game.calendar.current_date)
    game.install_player_club(club)
    return game, club


def test_sport_facilities_are_buildable():
    assert fac.spec("medical").buildable
    assert fac.spec("training").buildable
    assert fac.spec("oficina").buildable
    assert fac.spec("youth").buildable              # Complejo juvenil (cantera)
    assert fac.spec("youth").min_tier is LeagueTier.D


def test_medical_and_oficina_min_tier_anchor(monkeypatch):
    game, club = _game(11, monkeypatch)              # club en E
    assert fac.facility_status(club, "medical") == "locked_tier"   # E no puede
    assert fac.facility_status(club, "oficina") == "locked_tier"
    assert fac.facility_status(club, "training") == "buildable"    # E si
    club.tier = LeagueTier.D
    assert fac.facility_status(club, "medical") == "buildable"
    assert fac.facility_status(club, "oficina") == "buildable"


def test_slots_grow_with_home_facility(monkeypatch):
    game, club = _game(11, monkeypatch)
    assert staff.staff_slots(club, EmployeeRole.DOCTOR) == 1
    assert staff.staff_slots(club, EmployeeRole.FINANCE) == 1
    club.facilities["medical"] = 3
    club.facilities["oficina"] = 2
    assert staff.staff_slots(club, EmployeeRole.DOCTOR) == 4
    assert staff.staff_slots(club, EmployeeRole.FINANCE) == 3


def test_medical_reduces_injuries_without_doctor(monkeypatch):
    game, club = _game(11, monkeypatch)
    assert staff.injury_factor(club) == 1.0 and staff.injury_weeks_factor(club) == 1.0
    club.facilities["medical"] = 2
    assert staff.injury_factor(club) < 1.0          # la enfermeria sola baja lesiones
    assert staff.injury_weeks_factor(club) < 1.0


def test_office_adds_income_with_cap(monkeypatch):
    game, club = _game(11, monkeypatch)
    assert staff.income_bonus(club) == 0.0
    club.facilities["oficina"] = 2
    assert staff.income_bonus(club) > 0.0
    club.facilities["oficina"] = 3                  # combinado nunca pasa el tope
    assert staff.income_bonus(club) <= 0.20


def test_training_center_boosts_training(monkeypatch):
    game, club = _game(11, monkeypatch)
    club.formation_training["4-3-3"] = 40.0
    train_formation(club, "4-3-3", club.coach)
    gain_base = club.formation_training["4-3-3"] - 40.0

    club.formation_training["4-3-3"] = 40.0
    club.facilities["training"] = 3
    train_formation(club, "4-3-3", club.coach)
    gain_boosted = club.formation_training["4-3-3"] - 40.0
    assert gain_boosted > gain_base                 # el centro entrena mas rapido
