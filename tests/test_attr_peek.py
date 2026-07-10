"""Vistazo rapido de atributos inline en la tabla de plantilla (sin popup)."""

import asyncio

from tacticore import config
from tacticore.core.game import GameState
from tacticore.core.rng import new_rng
from tacticore.domain.manager import Manager
from tacticore.generators import ClubGenerator, WorldGenerator
from tacticore.persistence import savegame
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
    return game


def _screen_text(app):
    return "\n".join(s.text for s in app.screen._compositor.render_strips())


def test_attr_peek_toggles_and_follows_focus(monkeypatch):
    game = _game(monkeypatch)
    club = game.player_club

    async def run():
        app = TacticoreApp()
        async with app.run_test(size=(80, 25)) as pilot:
            app.game = game
            await app.push_screen(PlayersScreen())
            await pilot.pause()
            assert not app.screen._peek
            assert "Velocidad" not in _screen_text(app)     # sin panel al inicio

            await pilot.press("a")                            # abrir el panel
            await pilot.pause()
            assert app.screen._peek
            txt = _screen_text(app)
            assert "Velocidad" in txt and "Sacrificio" in txt  # los 15 atributos
            assert club.players[0].full_name in txt            # el jugador en foco
            # 80x25 ASCII
            for r in _screen_text(app).split("\n"):
                assert len(r.rstrip()) <= 80
                assert all(0x20 <= ord(c) <= 0x7E for c in r)

            await pilot.press("down")                         # el panel sigue al foco
            await pilot.press("down")
            await pilot.pause()
            assert club.players[2].full_name in _screen_text(app)

            await pilot.press("a")                            # cerrar el panel
            await pilot.pause()
            assert not app.screen._peek
            assert "Velocidad" not in _screen_text(app)

    asyncio.run(run())
