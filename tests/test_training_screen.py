"""Pantalla de Entrenamiento (sin pestanas: grid + informe navegable) + notif completa."""

import asyncio
import itertools

from tacticore import config
from tacticore.core.game import GameState
from tacticore.core.rng import new_rng
from tacticore.domain.manager import Manager
from tacticore.generators import ClubGenerator, WorldGenerator
from tacticore.persistence import savegame
from tacticore.simulation import notifications as notif
from tacticore.simulation import training as tr
from tacticore.ui.app import TacticoreApp
from tacticore.ui.screens.training_screen import TrainingScreen

_ATTRS = ["speed", "passing", "shooting", "stamina", "vision"]


def _game(monkeypatch, seed=7, weeks=0):
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
    for p, a in zip(club.players, itertools.cycle(_ATTRS)):
        tr.assign(p, a)
    for w in range(weeks):
        tr.run_training(game, new_rng(w + 1), game.calendar.current_date)
    return game, club


def test_training_notification_is_detailed():
    world = WorldGenerator(new_rng(3)).generate()
    game = GameState.new(seed=3, start_date=config.SEASON_START_DATE, countries=world)
    # (usa el mundo completo por defecto; alcanza con instalar un club del jugador)
    cc = world[0].code
    club = ClubGenerator(new_rng(3)).player_club(
        name="C", fans_name="F", stadium_name="S", manager=Manager("A", "B", cc),
        country_code=cc, today=game.calendar.current_date)
    game.install_player_club(club)
    for p, a in zip(club.players, itertools.cycle(_ATTRS)):
        tr.assign(p, a)
    tr.run_training(game, new_rng(1), game.calendar.current_date)
    reps = [n for n in game.notifications if n.category == notif.TRAINING]
    assert reps
    msg = reps[-1].message
    assert "Capacidad" in msg and "\n" in msg          # multilinea (detalle por jugador)
    assert any(line.strip().startswith(("+", "  ")) or "+" in line
               for line in msg.split("\n")[1:])         # renglones de mejora


def test_training_report_lines_columns_and_cap():
    from tacticore.ui.format import training_report_lines
    msg = "Resumen: 6 mejoras:\n" + "\n".join(
        f"  Jugador{i} +0.{i} Velocidad" for i in range(1, 7))
    lines = training_report_lines(msg, max_rows=4)   # 1 resumen + 3 filas de cuerpo
    assert lines[0].plain == "Resumen: 6 mejoras:"
    # 6 mejoras en 2 columnas -> 3 filas; cada fila tiene 2 mejoras (ancho <= 80).
    assert len(lines) == 1 + 3
    for ln in lines[1:]:
        assert len(ln.plain.rstrip()) <= 80
        assert "+0." in ln.plain
    # Con menos filas disponibles, se corta con "... y N mas".
    tight = training_report_lines(msg, max_rows=3)   # 1 resumen + 2 filas
    assert any("y" in ln.plain and "mas" in ln.plain for ln in tight)


def test_training_screen_no_tabs_grid_and_report(monkeypatch):
    game, club = _game(monkeypatch, weeks=2)

    async def run():
        app = TacticoreApp()
        async with app.run_test(size=(80, 25)) as pilot:
            app.game = game
            await app.push_screen(TrainingScreen())
            await pilot.pause()
            strips = [s.text for s in app.screen._compositor.render_strips()]
            txt = "\n".join(strips)
            assert "[1]" not in txt and "Historial" not in txt   # sin pestanas
            assert "ENTRENAMIENTO" in txt and "INFORME DE ENTRENAMIENTO" in txt
            assert "(1/2)" in txt                                # informe 1 de 2
            for r in strips:
                assert len(r.rstrip()) <= 80
                assert all(0x20 <= ord(c) <= 0x7E for c in r)
            # Ayuda a UN espacio del menu: hint en la fila 22, blanco en 23, menu en 24.
            assert "atributo" in strips[22] and "informe" in strips[22]
            assert strips[23].strip() == ""
            assert "[C]Club" in strips[24]

    asyncio.run(run())


def test_training_screen_navigates_reports_and_grid(monkeypatch):
    game, club = _game(monkeypatch, weeks=2)

    async def run():
        app = TacticoreApp()
        async with app.run_test(size=(80, 25)) as pilot:
            app.game = game
            await app.push_screen(TrainingScreen())
            await pilot.pause()
            scr = app.screen
            assert scr._report == 0 and scr._sel == 0
            await pilot.press("right")          # informe mas viejo
            await pilot.pause()
            assert scr._report == 1
            assert "(2/2)" in "\n".join(s.text for s in app.screen._compositor.render_strips())
            await pilot.press("left")           # de vuelta al mas nuevo
            await pilot.pause()
            assert scr._report == 0
            await pilot.press("down")           # mueve el atributo del grid
            await pilot.pause()
            assert scr._sel == 1

    asyncio.run(run())
