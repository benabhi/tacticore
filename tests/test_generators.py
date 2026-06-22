"""Tests de los generadores procedurales (determinismo)."""

from soccer_manager.core.rng import new_rng
from soccer_manager.generators import ClubGenerator, NameGenerator


def test_name_generator_is_deterministic():
    # Misma semilla -> mismos nombres.
    a = NameGenerator(new_rng(42)).player_name()
    b = NameGenerator(new_rng(42)).player_name()
    assert a == b


def test_club_has_two_goalkeepers():
    from soccer_manager.domain.enums import Position

    club = ClubGenerator(new_rng(7)).generate(squad_size=18)
    keepers = [p for p in club.players if p.position is Position.GOALKEEPER]
    assert club.squad_size == 18
    assert len(keepers) >= 2
