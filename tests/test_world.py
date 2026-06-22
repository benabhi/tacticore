"""Tests del generador del mundo."""

from tacticore import config
from tacticore.core.rng import new_rng
from tacticore.domain.enums import LeagueTier
from tacticore.generators import WorldGenerator


def test_world_is_deterministic():
    # Misma semilla -> mismo mundo completo.
    a = WorldGenerator(new_rng(123)).generate()
    b = WorldGenerator(new_rng(123)).generate()
    assert a == b


def test_world_structure():
    world = WorldGenerator(new_rng(1)).generate()
    assert len(world) == config.WORLD_COUNTRY_COUNT
    for country in world:
        # 5 ligas por pais, en orden A..E.
        assert [league.tier for league in country.leagues] == list(LeagueTier)
        for league in country.leagues:
            assert len(league.clubs) == config.CLUBS_PER_LEAGUE
            for club in league.clubs:
                assert club.squad_size == config.SQUAD_SIZE
                assert club.stadium.capacity > 0
                assert club.capital > 0
                assert club.country_code == country.code


def test_higher_tier_is_stronger():
    # El OVR promedio de los clubes debe bajar de la liga A a la E.
    world = WorldGenerator(new_rng(99)).generate()
    by_tier: dict[LeagueTier, list[int]] = {tier: [] for tier in LeagueTier}
    for country in world:
        for league in country.leagues:
            for club in league.clubs:
                by_tier[league.tier].append(club.overall)

    averages = [
        sum(by_tier[tier]) / len(by_tier[tier]) for tier in LeagueTier
    ]
    # Estrictamente decreciente: A > B > C > D > E.
    assert all(a > b for a, b in zip(averages, averages[1:]))


def test_progress_callback_reaches_total():
    calls: list[tuple[int, int]] = []
    WorldGenerator(new_rng(2)).generate(
        progress=lambda text, done, total: calls.append((done, total))
    )
    # El ultimo aviso debe llegar al total (barra llena).
    assert calls[-1][0] == calls[-1][1]
    assert calls[-1][1] == (
        config.WORLD_COUNTRY_COUNT * len(LeagueTier) * config.CLUBS_PER_LEAGUE
    )
