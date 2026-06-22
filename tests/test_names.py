"""Tests de la generacion de nombres por nacionalidad."""

from tacticore.core.rng import new_rng
from tacticore.generators.name_generator import NameGenerator
from tacticore.generators.name_pools import load_pool


def test_pool_loads_for_known_country():
    pool = load_pool("AR")
    assert pool is not None
    first_names, last_names = pool
    assert len(first_names) > 100 and len(last_names) > 100


def test_unknown_country_has_no_pool():
    assert load_pool("ZZ") is None


def test_player_name_uses_country_pool():
    first_names, last_names = load_pool("AR")
    first, last = NameGenerator(new_rng(1)).player_first_last("AR")
    assert first in first_names
    assert last in last_names


def test_name_is_deterministic_by_seed():
    a = NameGenerator(new_rng(7)).player_first_last("BR")
    b = NameGenerator(new_rng(7)).player_first_last("BR")
    assert a == b


def test_fallback_when_no_country():
    # Sin country_code usa el fallback silabico (no falla).
    first, last = NameGenerator(new_rng(3)).player_first_last()
    assert first and last
