"""TopBar (semana de 7 dias) y calendario de Club > Oficina (alternable + scroll)."""

import asyncio

from tacticore import config
from tacticore.core.game import GameState
from tacticore.core.rng import new_rng
from tacticore.domain.manager import Manager
from tacticore.generators import ClubGenerator, WorldGenerator
from tacticore.persistence import savegame
from tacticore.simulation.season import ensure_all_fixtures, ensure_player_friendlies
from tacticore.ui.app import TacticoreApp
from tacticore.ui.screens.club_screen import ClubScreen


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
    ensure_all_fixtures(game)
    ensure_player_friendlies(game)
    return game


def _screen_text(app):
    return "\n".join(s.text for s in app.screen._compositor.render_strips())


def test_topbar_shows_week_and_date(monkeypatch):
    game = _game(monkeypatch)

    async def run():
        app = TacticoreApp()
        async with app.run_test(size=(80, 25)) as pilot:
            app.game = game
            await app.push_screen(ClubScreen())
            await pilot.pause()
            top = app.screen._compositor.render_strips()[0].text
            for dow in ("Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"):
                assert dow in top
            assert game.calendar.current_date.strftime("%d-%m-%Y") in top
            assert "[Espacio] avanzar" in top          # el control se mantiene
            assert len(top.rstrip()) <= 80
            # La pestana principal ahora se llama Oficina.
            assert "Oficina" in app.screen._compositor.render_strips()[2].text

    asyncio.run(run())


def test_oficina_calendar_default_toggle_and_scroll(monkeypatch):
    game = _game(monkeypatch)

    async def run():
        app = TacticoreApp()
        async with app.run_test(size=(80, 25)) as pilot:
            app.game = game
            await app.push_screen(ClubScreen())
            await pilot.pause()
            scr = app.screen
            # Por defecto: calendario.
            assert scr._of_view == "calendar"
            txt = _screen_text(app)
            assert "CALENDARIO" in txt and "(esta semana)" in txt
            for r in txt.split("\n"):
                assert len(r.rstrip()) <= 80
                assert all(0x20 <= ord(c) <= 0x7E for c in r)
            # V alterna a estadisticas y de vuelta.
            await pilot.press("v")
            await pilot.pause()
            assert scr._of_view == "stats"
            assert "PLANTEL" in _screen_text(app) and "FINANZAS" in _screen_text(app)
            await pilot.press("v")
            await pilot.pause()
            assert scr._of_view == "calendar"
            # Las flechas mueven la semana de a 7 dias.
            assert scr._cal_offset == 0
            await pilot.press("right")
            await pilot.pause()
            assert scr._cal_offset == 7
            assert "(esta semana)" not in _screen_text(app)
            await pilot.press("left")
            await pilot.press("left")
            await pilot.pause()
            assert scr._cal_offset == -7
            # Esc vuelve a la semana actual desde donde sea.
            await pilot.press("escape")
            await pilot.pause()
            assert scr._cal_offset == 0 and "(esta semana)" in _screen_text(app)

    asyncio.run(run())


def test_novedades_table_above_calendar(monkeypatch):
    from tacticore.simulation import notifications as notif
    game = _game(monkeypatch)
    notif.notify(game, "Cierre economico",
                 "La caja quedo en $200.000 tras pagar sueldos, upkeep, socios y demas "
                 "gastos de la semana con detalle largo.", notif.FINANCE)
    notif.notify(game, "Fichaje", "Llego un juvenil", notif.MARKET)

    async def run():
        app = TacticoreApp()
        async with app.run_test(size=(80, 25)) as pilot:
            app.game = game
            await app.push_screen(ClubScreen())
            await pilot.pause()
            strips = [s.text for s in app.screen._compositor.render_strips()]
            # La tabla NOVEDADES va ARRIBA del calendario, con el contador sin leer.
            nov_row = next(y for y, r in enumerate(strips) if r.startswith("NOVEDADES"))
            cal_row = next(y for y, r in enumerate(strips) if "CALENDARIO" in r)
            assert nov_row < cal_row
            txt = "\n".join(strips)
            assert "sin leer" in txt and "[Finanzas]" in txt and "[Mercado]" in txt
            assert "Cierre economico" in txt
            # Las filas largas se recortan con "..." para indicar que hay mas.
            nrow = next(r for r in strips if "[Finanzas]" in r)
            assert nrow.rstrip().endswith("...")
            for r in strips:
                assert len(r.rstrip()) <= 80
                assert all(0x20 <= ord(c) <= 0x7E for c in r)

    asyncio.run(run())


def test_calendar_shows_match_events_abbreviated(monkeypatch):
    game = _game(monkeypatch)

    async def run():
        app = TacticoreApp()
        async with app.run_test(size=(80, 25)) as pilot:
            app.game = game
            await app.push_screen(ClubScreen())
            await pilot.pause()
            # La semana del club tiene amistoso (miercoles) y liga (domingo): el
            # calendario los muestra abreviados (Liga J#, Amistoso), SIN el rival.
            scr = app.screen
            found_match = found_liga = False
            for off in (0, 7, 14, 21):
                scr._cal_offset = off
                scr._refresh_content()
                await pilot.pause()
                # Solo el bloque del calendario (debajo de la regla), no el pantallazo
                # de arriba (que si muestra "vs Rival").
                strips = app.screen._compositor.render_strips()
                cal = "\n".join(s.text for s in strips[12:23])
                if "Amistoso" in cal:
                    found_match = True
                if "Liga J" in cal:
                    found_liga = True
                assert "vs " not in cal          # el rival NO va en el calendario
            assert found_match and found_liga

    asyncio.run(run())
