"""Tests de los generadores procedurales (determinismo)."""

from tacticore.core.rng import new_rng
from tacticore.generators import ClubGenerator, NameGenerator


def test_name_generator_is_deterministic():
    # Misma semilla -> mismos nombres.
    a = NameGenerator(new_rng(42)).player_name()
    b = NameGenerator(new_rng(42)).player_name()
    assert a == b


def test_club_has_two_goalkeepers():
    from tacticore.domain.enums import Position

    club = ClubGenerator(new_rng(7)).generate(squad_size=18)
    keepers = [p for p in club.players if p.position is Position.GOALKEEPER]
    assert club.squad_size == 18
    assert len(keepers) >= 2


def test_squad_meets_position_minimums():
    from collections import Counter

    from tacticore.domain.enums import LeagueTier, Position

    club = ClubGenerator(new_rng(11)).generate(squad_size=16, tier=LeagueTier.C)
    counts = Counter(p.position for p in club.players)
    assert counts[Position.GOALKEEPER] >= 2
    assert counts[Position.DEFENDER] >= 5
    assert counts[Position.MIDFIELDER] >= 5
    assert counts[Position.FORWARD] >= 3
    assert club.squad_size == 16


def test_generated_club_has_president():
    from datetime import date

    today = date(2025, 7, 1)
    club = ClubGenerator(new_rng(5)).generate(country_code="AR", today=today)
    assert club.president is not None
    assert club.president.nationality == "AR"
    assert club.president.age_on(today) >= 45


def test_club_name_is_ascii_and_well_formed():
    g = NameGenerator(new_rng(11))
    for _ in range(200):
        name = g.club_name()
        assert name == name.strip() and name          # sin bordes vacios
        assert all(32 <= ord(c) <= 126 for c in name)  # solo ASCII (directiva 2)


def test_club_name_is_deterministic_by_seed():
    assert NameGenerator(new_rng(7)).club_name() == NameGenerator(new_rng(7)).club_name()


def test_club_names_are_unique_in_bulk():
    # El generador debe dar muchos nombres sin repetir.
    names = NameGenerator(new_rng(3)).club_names(5000)
    assert len(names) == 5000
    assert len(set(names)) == 5000


def test_club_core_extracts_toponym():
    from tacticore.generators.name_generator import club_core

    assert club_core("Real Caldton United") == "Caldton"
    assert club_core("Eldford") == "Eldford"


def test_nicknames_and_fan_names_are_ascii_and_varied():
    g = NameGenerator(new_rng(4))
    nicks = {g.nickname() for _ in range(3000)}
    fans = {g.fan_group_name() for _ in range(3000)}
    assert len(nicks) > 300 and len(fans) > 200      # buena variedad
    for text in list(nicks)[:50] + list(fans)[:50]:
        assert all(32 <= ord(c) <= 126 for c in text)  # solo ASCII (directiva 2)


def test_manager_age_always_at_least_40():
    from datetime import date

    from tacticore.generators.manager_generator import ManagerGenerator

    today = date(2025, 7, 1)
    g = ManagerGenerator(new_rng(5))
    for _ in range(2000):
        manager = g.generate("AR", today)
        assert manager.age_on(today) >= 40
        assert manager.nationality == "AR"
        assert manager.first_name and manager.last_name


def test_manager_is_deterministic_by_seed():
    from datetime import date

    from tacticore.generators.manager_generator import ManagerGenerator

    today = date(2025, 7, 1)
    a = ManagerGenerator(new_rng(7)).generate("BR", today)
    b = ManagerGenerator(new_rng(7)).generate("BR", today)
    assert (a.full_name, a.birth_date) == (b.full_name, b.birth_date)


def test_generated_club_has_fans_and_manager():
    from datetime import date

    today = date(2025, 7, 1)
    club = ClubGenerator(new_rng(3)).generate(squad_size=16, today=today)
    assert club.fans_name
    assert club.manager is not None
    assert club.manager.age_on(today) >= 40
