"""UI de Club > Empleados: drill-down por rol (contratar, reemplazar DT, despedir)."""

import asyncio

from tacticore import config
from tacticore.core.game import GameState
from tacticore.core.rng import new_rng
from tacticore.domain.enums import EmployeeRole
from tacticore.domain.manager import Manager
from tacticore.generators import ClubGenerator, WorldGenerator
from tacticore.persistence import savegame
from tacticore.simulation import staff
from tacticore.ui.app import TacticoreApp
from tacticore.ui.screens.club_screen import ClubScreen

_EMP_TAB = 3  # indice de la pestana Empleados


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


def test_empleados_renders_all_roles_80_ascii(monkeypatch):
    game = _game(monkeypatch)

    async def run():
        app = TacticoreApp()
        async with app.run_test(size=(80, 25)) as pilot:
            app.game = game
            await app.push_screen(ClubScreen())
            await pilot.pause()
            await pilot.press(str(_EMP_TAB + 1))  # tecla '4' -> Empleados
            await pilot.pause()
            # Recorrer todos los roles con -> y validar ancho/ASCII en cada uno.
            for _ in range(6):
                rows = [s.text for s in app.screen._compositor.render_strips()]
                for r in rows:
                    assert len(r.rstrip()) <= 80
                    assert all(0x20 <= ord(c) <= 0x7E for c in r)
                await pilot.press("right")
                await pilot.pause()

    asyncio.run(run())


def test_hire_replace_fire_flow(monkeypatch):
    game = _game(monkeypatch)
    club = game.player_club

    async def run():
        app = TacticoreApp()
        async with app.run_test(size=(80, 25)) as pilot:
            app.game = game
            await app.push_screen(ClubScreen())
            await pilot.pause()
            await pilot.press("4")
            await pilot.pause()
            # Rol 0 = DT: bajar a un candidato y reemplazar.
            old = club.coach
            await pilot.press("down")
            await pilot.press("enter")
            await pilot.pause()
            assert club.coach is not old            # DT reemplazado
            # DT no se puede despedir.
            keep = club.coach
            await pilot.press("delete")
            await pilot.pause()
            assert club.coach is keep
            # Ir a Medico y contratar un candidato.
            await pilot.press("right")
            await pilot.pause()
            assert staff.role_count(club, EmployeeRole.DOCTOR) == 0
            await pilot.press("enter")
            await pilot.pause()
            assert staff.role_count(club, EmployeeRole.DOCTOR) == 1
            # Despedir al recien contratado (esta primero en la lista).
            await pilot.press("up")
            await pilot.press("delete")
            await pilot.pause()
            assert staff.role_count(club, EmployeeRole.DOCTOR) == 0

    asyncio.run(run())
