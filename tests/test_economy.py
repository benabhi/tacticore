"""Tests de la economia base (valor y sueldo de un jugador)."""

from datetime import date

from tacticore.domain.enums import Foot, Position
from tacticore.domain.player import ALL_ATTRS, Player
from tacticore.simulation.economy import (
    STARTING_BUDGET,
    player_salary,
    player_value,
    squad_wage_bill,
)

_TODAY = date(2025, 7, 1)


def _player(level: float, age: int, potential: float | None = None) -> Player:
    """Jugador con TODOS los atributos en `level` (asi el overall == level)."""
    p = Player(
        first_name="A", last_name="B", nationality="AR", position=Position.STRIKER,
        foot=Foot.RIGHT, birth_date=date(_TODAY.year - age, 1, 1),
        height_cm=180, weight_kg=75,
    )
    for attr in ALL_ATTRS:
        setattr(p, attr, float(level))
    p.potential = float(level if potential is None else potential)
    return p


def test_starting_budget_is_small():
    assert STARTING_BUDGET == 200_000


def test_salary_has_a_floor():
    # Hasta el peor jugador cobra el minimo.
    assert player_salary(_player(1, age=25), _TODAY) >= 400


def test_salary_grows_with_overall():
    weak = player_salary(_player(30, age=25), _TODAY)
    strong = player_salary(_player(60, age=25), _TODAY)
    assert strong > weak


def test_value_grows_with_overall():
    assert player_value(_player(60, age=25), _TODAY) > player_value(_player(40, age=25), _TODAY)


def test_value_decays_with_age():
    young = player_value(_player(50, age=18), _TODAY)
    old = player_value(_player(50, age=34), _TODAY)
    assert young > old


def test_potential_adds_value():
    plain = player_value(_player(50, age=20, potential=50), _TODAY)
    promising = player_value(_player(50, age=20, potential=80), _TODAY)
    assert promising > plain


def test_is_deterministic():
    p = _player(45, age=27)
    assert player_salary(p, _TODAY) == player_salary(p, _TODAY)
    assert player_value(p, _TODAY) == player_value(p, _TODAY)


def test_wage_bill_sums_salaries():
    squad = [_player(40, 22), _player(55, 28), _player(30, 33)]
    expected = sum(player_salary(p, _TODAY) for p in squad)
    assert squad_wage_bill(squad, _TODAY) == expected
