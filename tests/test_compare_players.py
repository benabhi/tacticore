"""Tests de la comparacion "versus" entre dos jugadores (helpers + pantalla)."""

import asyncio
from datetime import date

from tacticore import config
from tacticore.core.game import GameState
from tacticore.core.rng import new_rng
from tacticore.domain.enums import Position
from tacticore.domain.manager import Manager
from tacticore.generators import ClubGenerator, PlayerGenerator, WorldGenerator
from tacticore.persistence import savegame
from tacticore.ui.app import TacticoreApp
from tacticore.ui.screens.compare_players_screen import (
    _BAR_HALF, ComparePlayersScreen, _cmp_style, _diverge_bar, _tally)
from tacticore.ui.screens.players_screen import PlayersScreen

_TODAY = date(2026, 7, 10)


def _two_players():
    a = PlayerGenerator(new_rng(1)).generate(Position.STRIKER)
    b = PlayerGenerator(new_rng(2)).generate(Position.CENTER_BACK)
    return a, b


# --- Helpers puros ---
def test_cmp_style_green_red_grey():
    assert _cmp_style(5.0, 3.0) == "bold green"  # mas alto -> verde
    assert _cmp_style(3.0, 5.0) == "red"         # mas bajo -> rojo
    assert _cmp_style(4.0, 4.0) == "grey62"      # empate -> gris


def test_diverge_bar_points_to_winner_and_is_ascii():
    width = 2 * _BAR_HALF + 1
    a_wins = _diverge_bar(80.0, 50.0)
    b_wins = _diverge_bar(50.0, 80.0)
    tie = _diverge_bar(50.0, 50.0)
    for bar in (a_wins, b_wins, tie):
        assert len(bar) == width
        assert bar[_BAR_HALF] == "|"                 # centro
        assert all(0x20 <= ord(c) <= 0x7E for c in bar)
    # A gana -> relleno a la IZQUIERDA del centro; B gana -> a la DERECHA.
    assert "#" in a_wins[:_BAR_HALF] and "#" not in a_wins[_BAR_HALF + 1:]
    assert "#" in b_wins[_BAR_HALF + 1:] and "#" not in b_wins[:_BAR_HALF]
    assert "#" not in tie                            # empate -> sin relleno


def test_diverge_bar_magnitude_caps_at_half():
    full = _diverge_bar(100.0, 1.0)  # diferencia enorme -> media barra llena
    assert full.count("#") == _BAR_HALF


def test_tally_counts_over_all_attributes():
    a, b = _two_players()
    wa, wb, ties = _tally(a, b)
    assert wa + wb + ties == 15  # 15 atributos
    # Simetria: invertir los jugadores intercambia ganados.
    assert _tally(b, a) == (wb, wa, ties)


# --- Render de la pantalla (sin app montada) ---
def test_card_text_fits_80x25_and_is_ascii():
    a, b = _two_players()
    screen = ComparePlayersScreen(a, b, _TODAY)
    lines = screen._card_text().plain.split("\n")
    assert len(lines) <= 24  # entra en el viewport (deja la fila de ayuda)
    for ln in lines:
        assert len(ln) <= 80, f"linea de {len(ln)} > 80: {ln!r}"
        assert all(0x20 <= ord(c) <= 0x7E for c in ln), f"no-ASCII en {ln!r}"


def test_card_text_respects_side_order():
    a, b = _two_players()
    screen = ComparePlayersScreen(a, b, _TODAY)
    first = screen._card_text().plain.split("\n")[0]
    assert a.full_name in first and "(A)" in first
    # Intercambiar los lados invierte la cabecera.
    screen._a, screen._b = screen._b, screen._a
    first = screen._card_text().plain.split("\n")[0]
    assert b.full_name in first and first.index(b.full_name) < first.index("(A)")


# --- Flujo de seleccion en la Plantilla (headless) ---
def _game(monkeypatch, seed=7):
    monkeypatch.setattr(config, "WORLD_COUNTRY_COUNT", 2)
    world = WorldGenerator(new_rng(seed)).generate()
    game = GameState.new(seed=seed, start_date=config.SEASON_START_DATE, countries=world)
    cc = world[0].code
    club = ClubGenerator(new_rng(seed)).player_club(
        name="Mi Club", fans_name="F", stadium_name="S",
        manager=Manager("A", "B", cc), country_code=cc,
        today=game.calendar.current_date)
    game.install_player_club(club)
    return game


def test_mark_and_open_comparison(monkeypatch):
    monkeypatch.setattr(savegame, "save_game", lambda *a, **k: None)
    game = _game(monkeypatch)

    async def run():
        app = TacticoreApp()
        async with app.run_test(size=(80, 25)) as pilot:
            app.game = game
            await app.push_screen(PlayersScreen())
            await pilot.pause()
            # Marcar al jugador en foco (A) y elegir el siguiente (B) con Enter.
            await pilot.press("m")
            await pilot.pause()
            assert app.screen._compare_from is game.player_club.players[0]
            await pilot.press("down")
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, ComparePlayersScreen)
            # Volver limpia la marca de comparacion.
            await pilot.press("escape")
            await pilot.pause()
            assert isinstance(app.screen, PlayersScreen)
            assert app.screen._compare_from is None

    asyncio.run(run())


def test_escape_cancels_compare_mode(monkeypatch):
    monkeypatch.setattr(savegame, "save_game", lambda *a, **k: None)
    game = _game(monkeypatch)

    async def run():
        app = TacticoreApp()
        async with app.run_test(size=(80, 25)) as pilot:
            app.game = game
            await app.push_screen(PlayersScreen())
            await pilot.pause()
            await pilot.press("m")
            await pilot.pause()
            assert app.screen._compare_from is not None
            await pilot.press("escape")   # cancela sin abrir la comparacion
            await pilot.pause()
            assert isinstance(app.screen, PlayersScreen)
            assert app.screen._compare_from is None

    asyncio.run(run())
