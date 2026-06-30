"""Tests del modelo de jugador y su generador."""

from datetime import date

from tacticore.core.rng import new_rng
from tacticore.domain.enums import LeagueTier, Position
from tacticore.domain.player import ALL_ATTRS
from tacticore.generators import PlayerGenerator


def test_generated_player_is_deterministic():
    a = PlayerGenerator(new_rng(1)).generate(Position.STRIKER)
    b = PlayerGenerator(new_rng(1)).generate(Position.STRIKER)
    assert a == b


def test_attributes_in_valid_range():
    player = PlayerGenerator(new_rng(3)).generate()
    for attr in ALL_ATTRS:
        value = getattr(player, attr)
        assert 1.0 <= value <= 100.0, f"{attr}={value} fuera de 1-100"
    assert 1.0 <= player.overall <= 100.0


def test_attributes_are_floats_with_variety():
    # Deben ser float (permiten decimales) y variados, no todos iguales.
    player = PlayerGenerator(new_rng(8)).generate()
    values = [getattr(player, attr) for attr in ALL_ATTRS]
    assert all(isinstance(v, float) for v in values)
    assert len(set(values)) > 5  # hay variedad de valores


def test_goalkeeper_profile():
    # Un arquero se apoya en atributos generales: agilidad alta, remate bajo.
    gk = PlayerGenerator(new_rng(5)).generate(Position.GOALKEEPER, LeagueTier.A)
    assert gk.agility > gk.shooting
    assert gk.agility >= 70  # en liga A, agilidad de elite bajo los palos


def test_attribute_groups_are_three_of_five():
    from tacticore.domain.player import (
        MENTAL_ATTRS,
        PHYSICAL_ATTRS,
        TECHNICAL_ATTRS,
    )

    assert len(ALL_ATTRS) == 15
    assert len(PHYSICAL_ATTRS) == len(TECHNICAL_ATTRS) == len(MENTAL_ATTRS) == 5


def test_position_priorities_cover_all_attributes():
    # Las 12 posiciones existen, tienen 5 atributos validos cada una, y entre
    # todas usan los 15 atributos (todos pesan en alguna posicion).
    from tacticore.domain.enums import Position
    from tacticore.domain.positions import POSITION_PRIORITIES

    assert set(POSITION_PRIORITIES) == set(Position)
    used = set()
    for attrs in POSITION_PRIORITIES.values():
        assert len(attrs) == 5
        assert all(a in ALL_ATTRS for a in attrs)
        used.update(attrs)
    assert used == set(ALL_ATTRS)


def test_experience_grows_with_age():
    from tacticore.domain.enums import Position

    gen = PlayerGenerator(new_rng(4))
    young = [p for _ in range(200) if (p := gen.generate(Position.CENTER_MID)).age_on(date(2025, 7, 1)) <= 18]
    veterans = [p for _ in range(200) if (p := gen.generate(Position.CENTER_MID)).age_on(date(2025, 7, 1)) >= 32]
    avg_young = sum(p.experience for p in young) / len(young)
    avg_vet = sum(p.experience for p in veterans) / len(veterans)
    assert avg_vet > avg_young


def test_age_is_derived_from_birth_date_and_ages_over_time():
    today = date(2025, 7, 1)
    player = PlayerGenerator(new_rng(1)).generate(today=today)
    age = player.age_on(today)
    assert 15 <= age <= 37  # rango razonable de un plantel
    # Un anio despues del juego, el jugador es un anio mas viejo (envejece solo).
    assert player.age_on(date(2026, 7, 1)) == age + 1


def test_nationality_comes_from_country_code():
    player = PlayerGenerator(new_rng(1)).generate(country_code="AR")
    assert player.nationality == "AR"


def test_display_name_prefers_nickname():
    player = PlayerGenerator(new_rng(2)).generate()
    player.nickname = "La Pulga"
    assert player.display_name == "La Pulga"
    player.nickname = None
    assert player.display_name == player.full_name
