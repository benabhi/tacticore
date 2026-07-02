"""Tests del estado raiz del juego (GameState)."""

from tacticore import config
from tacticore.core.game import GameState
from tacticore.core.rng import new_rng
from tacticore.domain.manager import Manager
from tacticore.generators import ClubGenerator, WorldGenerator


def _game_with_player_club(seed: int, monkeypatch):
    monkeypatch.setattr(config, "WORLD_COUNTRY_COUNT", 2)
    world = WorldGenerator(new_rng(seed)).generate()
    game = GameState.new(seed=seed, start_date=config.SEASON_START_DATE, countries=world)
    cc = world[0].code
    club = ClubGenerator(new_rng(seed)).player_club(
        name="Mi Club", fans_name="F", stadium_name="S",
        manager=Manager("A", "B", cc), country_code=cc,
    )
    game.install_player_club(club)
    return game, club, cc


def test_player_country_has_five_divisions(monkeypatch):
    game, club, cc = _game_with_player_club(5, monkeypatch)
    country = game.player_country
    assert country is not None
    assert country.code == cc
    # Cada pais tiene 5 ligas (niveles A-E).
    assert len(country.leagues) == 5
    # El club del jugador vive en una de esas ligas.
    assert any(club is c for lg in country.leagues for c in lg.clubs)


def test_player_country_is_none_without_club():
    game = GameState.new(seed=1, start_date=config.SEASON_START_DATE)
    assert game.player_country is None
