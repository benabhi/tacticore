"""Despedir jugadores (recision): gratis, nunca deja el plantel con menos de 11."""

import asyncio

from tacticore import config
from tacticore.core.game import GameState
from tacticore.core.rng import new_rng
from tacticore.domain.manager import Manager
from tacticore.generators import ClubGenerator, WorldGenerator
from tacticore.persistence import savegame
from tacticore.simulation import transfers as T
from tacticore.ui.app import TacticoreApp
from tacticore.ui.screens.players_screen import PlayersScreen


def _game(monkeypatch, seed=7):
    monkeypatch.setattr(config, "WORLD_COUNTRY_COUNT", 2)
    monkeypatch.setattr(savegame, "save_game", lambda *a, **k: None)
    world = WorldGenerator(new_rng(seed)).generate()
    game = GameState.new(seed=seed, start_date=config.SEASON_START_DATE, countries=world)
    cc = world[0].code
    club = ClubGenerator(new_rng(seed)).player_club(
        name="Mi Club", fans_name="F", stadium_name="S",
        manager=Manager("A", "B", cc), country_code=cc,
        today=game.calendar.current_date)
    game.install_player_club(club)
    return game, club


def test_release_removes_player_for_free(monkeypatch):
    game, club = _game(monkeypatch)
    before, cash = len(club.players), club.capital
    victim = club.players[3]
    assert T.release_player(club, victim)
    assert victim not in club.players
    assert len(club.players) == before - 1
    assert club.capital == cash              # es recision, no venta: no entra plata


def test_release_stops_at_min_roster(monkeypatch):
    game, club = _game(monkeypatch)
    while len(club.players) > T.MIN_ROSTER:
        assert T.release_player(club, club.players[-1])
    assert len(club.players) == T.MIN_ROSTER == 11
    assert not T.can_release(club)
    assert not T.release_player(club, club.players[0])   # no baja de 11
    assert len(club.players) == 11


def test_release_ignores_player_not_in_squad(monkeypatch):
    game, club = _game(monkeypatch)
    other = game.countries[0].leagues[-1].clubs[1].players[0]  # de otro club
    assert not T.release_player(club, other)


def test_release_ui_confirm_flow(monkeypatch):
    game, club = _game(monkeypatch)

    async def run():
        app = TacticoreApp()
        async with app.run_test(size=(80, 25)) as pilot:
            app.game = game
            await app.push_screen(PlayersScreen())
            await pilot.pause()
            before = len(club.players)
            # 'd' abre la confirmacion; Esc cancela (no despide).
            await pilot.press("d")
            await pilot.pause()
            assert app.screen._releasing is not None
            await pilot.press("escape")
            await pilot.pause()
            assert app.screen._releasing is None
            assert len(club.players) == before
            # 'd' + Enter despide (y respeta ancho/ASCII en la barra de confirmacion).
            await pilot.press("d")
            await pilot.pause()
            for r in [s.text for s in app.screen._compositor.render_strips()]:
                assert len(r.rstrip()) <= 80
                assert all(0x20 <= ord(c) <= 0x7E for c in r)
            await pilot.press("enter")
            await pilot.pause()
            assert len(club.players) == before - 1

    asyncio.run(run())
