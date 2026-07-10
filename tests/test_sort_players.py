"""Ordenar la plantilla por cualquier atributo (asc/desc) desde el selector."""

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


def test_sort_visible_by_overall_and_invert(monkeypatch):
    game = _game(monkeypatch)

    async def run():
        app = TacticoreApp()
        async with app.run_test(size=(80, 25)) as pilot:
            app.game = game
            await app.push_screen(PlayersScreen())
            await pilot.pause()
            scr = app.screen
            # Sin orden: coincide con el orden de plantel.
            assert scr._sort_key is None
            assert scr._visible() == game.player_club.players
            # O abre el selector; OVR esta primero -> Enter aplica OVR desc.
            await pilot.press("o")
            await pilot.pause()
            assert scr._sorting
            for r in [s.text for s in app.screen._compositor.render_strips()]:
                assert len(r.rstrip()) <= 80
                assert all(0x20 <= ord(c) <= 0x7E for c in r)
            await pilot.press("enter")
            await pilot.pause()
            assert scr._sort_key == "ovr" and scr._sort_desc
            ovrs = [p.overall for p in scr._visible()]
            assert ovrs == sorted(ovrs, reverse=True)     # descendente
            # Repetir el mismo campo invierte a ascendente.
            await pilot.press("o")
            await pilot.press("enter")
            await pilot.pause()
            assert not scr._sort_desc
            ovrs = [p.overall for p in scr._visible()]
            assert ovrs == sorted(ovrs)                   # ascendente

    asyncio.run(run())


def test_sort_by_attribute_and_text(monkeypatch):
    game = _game(monkeypatch)

    async def run():
        app = TacticoreApp()
        async with app.run_test(size=(80, 25)) as pilot:
            app.game = game
            await app.push_screen(PlayersScreen())
            await pilot.pause()
            scr = app.screen
            # Nombre (RESUMEN, fila 6) -> texto ascendente por defecto.
            await pilot.press("o")
            for _ in range(6):
                await pilot.press("down")
            await pilot.press("enter")
            await pilot.pause()
            assert scr._sort_key == "name" and not scr._sort_desc  # texto = asc
            names = [p.last_name.lower() for p in scr._visible()]
            assert names == sorted(names)
            # Un atributo (MENTALES, columna 3, fila 0 = Vision) -> numerico desc.
            # El selector reabre sobre el campo actual: subo a la fila 0 y voy a col 3.
            await pilot.press("o")
            for _ in range(9):
                await pilot.press("up")     # a la fila 0 (clamp)
            for _ in range(3):
                await pilot.press("right")  # a MENTALES, fila 0 = Vision
            await pilot.press("enter")
            await pilot.pause()
            assert scr._sort_key == "vision" and scr._sort_desc
            vals = [p.vision for p in scr._visible()]
            assert vals == sorted(vals, reverse=True)

    asyncio.run(run())


def test_sort_escape_keeps_previous(monkeypatch):
    game = _game(monkeypatch)

    async def run():
        app = TacticoreApp()
        async with app.run_test(size=(80, 25)) as pilot:
            app.game = game
            await app.push_screen(PlayersScreen())
            await pilot.pause()
            scr = app.screen
            await pilot.press("o")      # abrir
            await pilot.press("down")   # mover
            await pilot.press("escape")  # cancelar
            await pilot.pause()
            assert not scr._sorting and scr._sort_key is None   # sin cambios

    asyncio.run(run())
