"""Notificaciones: Enter despliega el detalle completo (y abre el modal si es evento)."""

import asyncio

from tacticore import config
from tacticore.core.game import GameState
from tacticore.core.rng import new_rng
from tacticore.domain.manager import Manager
from tacticore.generators import ClubGenerator, WorldGenerator
from tacticore.persistence import savegame
from tacticore.simulation import notifications as notif
from tacticore.ui.app import TacticoreApp
from tacticore.ui.screens.club_screen import ClubScreen

_NOTIF_TAB_KEY = "2"


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


def _txt(app):
    return "\n".join(s.text for s in app.screen._compositor.render_strips())


def test_enter_expands_full_detail(monkeypatch):
    game = _game(monkeypatch)
    notif.notify(game, "Entrenamiento: 3 mejoras",
                 "Capacidad 40. Entrenaron 12, mejoraron 3:\n"
                 "  Ana +0.7 Velocidad\n  Beto +0.4 Pase\n  Caio +0.2 Remate",
                 notif.TRAINING)

    async def run():
        app = TacticoreApp()
        async with app.run_test(size=(80, 25)) as pilot:
            app.game = game
            await app.push_screen(ClubScreen())
            await pilot.pause()
            await pilot.press(_NOTIF_TAB_KEY)
            await pilot.pause()
            assert not app.screen._notif_expanded
            # En la lista, el detalle multilinea NO se ve entero.
            assert "Beto +0.4 Pase" not in _txt(app)
            await pilot.press("enter")             # desplegar
            await pilot.pause()
            assert app.screen._notif_expanded
            txt = _txt(app)
            assert "NOTIFICACION" in txt and "[Entreno]" in txt
            # Ahora SI se ve el detalle completo (formateado en columnas legibles).
            assert "Ana" in txt and "+0.7 Velocidad" in txt
            assert "Beto" in txt and "+0.4 Pase" in txt
            assert "Caio" in txt and "+0.2 Remate" in txt
            for r in _txt(app).split("\n"):
                assert len(r.rstrip()) <= 80
                assert all(0x20 <= ord(c) <= 0x7E for c in r)
            await pilot.press("escape")            # volver a la lista
            await pilot.pause()
            assert not app.screen._notif_expanded

    asyncio.run(run())


def test_enter_on_pending_event_opens_modal(monkeypatch):
    game = _game(monkeypatch)
    notif.notify(game, "Oferta de patrocinio", "Una marca quiere firmar.",
                 notif.MARKET, kind=notif.EVENT_SPONSOR_OFFER,
                 payload={"name": "ACME", "sector": "Camiseta", "tier": 3,
                          "weekly_pay": 1000, "weeks_total": 20, "signing_bonus": 5000,
                          "promotion_bonus": 0, "streak_bonus": 0, "streak_len": 0,
                          "expires": "2027-01-01"})

    async def run():
        app = TacticoreApp()
        async with app.run_test(size=(80, 25)) as pilot:
            app.game = game
            await app.push_screen(ClubScreen())
            await pilot.pause()
            await pilot.press(_NOTIF_TAB_KEY)
            await pilot.pause()
            await pilot.press("enter")             # evento pendiente -> abre el modal
            await pilot.pause()
            assert app.screen.__class__.__name__ == "SponsorOfferScreen"

    asyncio.run(run())
