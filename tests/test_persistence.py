"""Tests de persistencia: guardar y cargar una partida (round-trip)."""

from tacticore import config
from tacticore.core.game import GameState
from tacticore.core.rng import new_rng
from tacticore.domain.president import President
from tacticore.generators import ClubGenerator, WorldGenerator
from tacticore.persistence import savegame


def _build_game(seed: int) -> GameState:
    """Arma una partida con un mundo chico y el club del jugador instalado."""
    world = WorldGenerator(new_rng(seed)).generate()
    game = GameState.new(
        seed=seed, start_date=config.SEASON_START_DATE, countries=world
    )
    country_code = world[0].code
    human = President(first_name="Pep", last_name="Guardiola", nationality=country_code)
    club = ClubGenerator(new_rng(seed)).player_club(
        name="Mi Club",
        fans_name="La Furia",
        stadium_name="El Templo",
        president=human,
        country_code=country_code,
    )
    game.install_player_club(club)
    game.president_name = "Pep Guardiola"
    return game


def test_save_load_round_trip(tmp_path, monkeypatch):
    # Mundo chico para que el test sea rapido.
    monkeypatch.setattr(config, "WORLD_COUNTRY_COUNT", 2)
    game = _build_game(7)
    path = tmp_path / "save.sqlite"

    assert not savegame.save_exists(path)
    savegame.save_game(game, path)
    assert savegame.save_exists(path)

    loaded = savegame.load_game(path)
    assert loaded.seed == game.seed
    assert loaded.calendar.current_date == game.calendar.current_date
    assert loaded.president_name == "Pep Guardiola"
    # El grafo entero se reconstruye identico (igualdad profunda de dataclasses).
    assert loaded.countries == game.countries


def test_player_club_is_reconnected_after_load(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "WORLD_COUNTRY_COUNT", 2)
    game = _build_game(3)
    path = tmp_path / "save.sqlite"
    savegame.save_game(game, path)

    loaded = savegame.load_game(path)
    assert loaded.player_club is not None
    assert loaded.player_club.name == "Mi Club"
    assert loaded.player_club.members == 500
    # El club del jugador es el MISMO objeto que vive dentro del grafo del mundo.
    in_world = [
        club
        for country in loaded.countries
        for league in country.leagues
        for club in league.clubs
    ]
    assert any(loaded.player_club is club for club in in_world)
