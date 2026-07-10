"""Cantera: generacion de juveniles, ojeadores, camadas, revelado y persistencia."""

import asyncio
import sqlite3
from datetime import date, timedelta

from tacticore import config
from tacticore.core.game import GameState
from tacticore.core.rng import new_rng
from tacticore.domain.enums import BonusType, EmployeeRole, LeagueTier
from tacticore.domain.employee import Employee
from tacticore.domain.manager import Manager
from tacticore.domain.player import ALL_ATTRS
from tacticore.domain.positions import POSITION_PRIORITIES
from tacticore.generators import ClubGenerator, PlayerGenerator, WorldGenerator
from tacticore.persistence import _db, savegame
from tacticore.simulation import staff, youth
from tacticore.simulation.season import ensure_all_fixtures
from tacticore.simulation.transfers import MAX_SQUAD
from tacticore.ui.app import TacticoreApp
from tacticore.ui.screens.players_screen import PlayersScreen

_TODAY = config.SEASON_START_DATE


def _game(monkeypatch, seed=7, scouts=2, youth_level=2):
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
    club.tier = LeagueTier.D
    club.facilities["youth"] = youth_level
    for i in range(scouts):
        skill = 40.0 + i * 45.0
        club.employees.append(Employee(EmployeeRole.SCOUT, "Oj", str(i), cc,
                                        date(1980, 1, 1), {BonusType.SCOUTING: skill},
                                        staff.staff_wage(skill, club.tier)))
    return game, club


# --- Generacion de juveniles ---
def test_generate_youth_is_young_capped_and_has_standout():
    for s in range(150):
        p = PlayerGenerator(new_rng(s)).generate_youth(LeagueTier.C, 70, "AR", _TODAY)
        assert 15 <= p.age_on(_TODAY) <= 18
        assert p.potential > p.overall                     # margen de crecimiento
        assert p.potential <= 95                           # nunca desbocado
        # ningun atributo por encima del techo (potencial)
        assert all(getattr(p, a) <= p.potential for a in ALL_ATTRS)


def test_youth_potential_scales_with_scout_and_tier():
    def avg_pot(tier, skill):
        pots = [PlayerGenerator(new_rng(s)).generate_youth(tier, skill, "AR", _TODAY).potential
                for s in range(120)]
        return sum(pots) / len(pots)
    assert avg_pot(LeagueTier.D, 30) < avg_pot(LeagueTier.D, 90)   # mejor ojeador
    assert avg_pot(LeagueTier.D, 60) < avg_pot(LeagueTier.A, 60)   # mejor liga


# --- Cupo de ojeadores (atado al Complejo juvenil) ---
def test_scout_slots_follow_youth_building(monkeypatch):
    game, club = _game(monkeypatch, youth_level=0)
    club.facilities["youth"] = 0
    assert staff.staff_slots(club, EmployeeRole.SCOUT) == 0     # sin edificio, sin ojeadores
    club.facilities["youth"] = 2
    assert staff.staff_slots(club, EmployeeRole.SCOUT) == 2
    club.facilities["youth"] = 5                                # tope duro 3
    assert staff.staff_slots(club, EmployeeRole.SCOUT) == 3


# --- Revelado segun la calidad del ojeador ---
def test_reveal_count_grows_with_skill():
    assert youth.reveal_count(20) < youth.reveal_count(50) < youth.reveal_count(70)
    assert youth.reveal_count(90) == len(ALL_ATTRS)


def test_revealed_attrs_deterministic_and_includes_standout():
    p = PlayerGenerator(new_rng(1)).generate_youth(LeagueTier.C, 55, "AR", _TODAY)
    from tacticore.domain.prospect import Prospect
    pr = Prospect(p, 55, _TODAY, _TODAY + timedelta(weeks=8))
    a = youth.revealed_attrs(pr)
    b = youth.revealed_attrs(pr)
    assert a == b                                              # determinista
    assert POSITION_PRIORITIES[p.position][0] in a            # incluye el destacado
    assert len(a) == youth.reveal_count(55)


# --- Camada, fichar y descartar ---
def test_intake_brings_one_prospect_per_scout(monkeypatch):
    game, club = _game(monkeypatch, scouts=2)
    d = youth.intake_dates(game)[0]
    assert len(youth.intake_dates(game)) == 2                 # dos por temporada
    youth.run_intake(game, d, new_rng(1))
    assert len(club.prospects) == 2                           # uno por ojeador
    # Determinista: misma semilla/fecha -> mismos juveniles.
    game2, club2 = _game(monkeypatch, scouts=2)
    youth.run_intake(game2, d, new_rng(1))
    assert [pr.player.full_name for pr in club.prospects] == \
           [pr.player.full_name for pr in club2.prospects]


def test_intake_only_on_intake_dates(monkeypatch):
    game, club = _game(monkeypatch)
    not_intake = youth.intake_dates(game)[0] + timedelta(days=1)
    youth.run_intake(game, not_intake, new_rng(1))
    assert club.prospects == []


def test_sign_moves_to_squad_and_respects_max(monkeypatch):
    game, club = _game(monkeypatch, scouts=1)
    d = youth.intake_dates(game)[0]
    youth.run_intake(game, d, new_rng(1))
    pr = club.prospects[0]
    before = len(club.players)
    assert youth.sign(game, pr)
    assert len(club.players) == before + 1
    assert pr.player in club.players and pr not in club.prospects
    assert club.players[-1].shirt_number is not None
    # Con el plantel lleno (MAX_SQUAD) no se puede fichar.
    youth.run_intake(game, d, new_rng(2))
    while len(club.players) < MAX_SQUAD:
        club.players.append(club.players[0])
    assert not youth.sign(game, club.prospects[0])


def test_discard_and_prune_expired(monkeypatch):
    game, club = _game(monkeypatch, scouts=2)
    d = youth.intake_dates(game)[0]
    youth.run_intake(game, d, new_rng(1))
    youth.discard(game, club.prospects[0])
    assert len(club.prospects) == 1
    # Al pasar la fecha de vencimiento, la poda los saca.
    youth.run_intake(game, club.prospects[0].expires + timedelta(days=1), new_rng(1))
    assert club.prospects == []


# --- Persistencia ---
def test_round_trip_prospects(monkeypatch):
    game, club = _game(monkeypatch, scouts=2)
    d = youth.intake_dates(game)[0]
    youth.run_intake(game, d, new_rng(1))
    youth.reveal(club.prospects[0])
    names = [pr.player.full_name for pr in club.prospects]
    conn = sqlite3.connect(":memory:")
    _db.write_game(conn, game)
    g2 = _db.read_game(conn)
    ps = g2.player_club.prospects
    assert [pr.player.full_name for pr in ps] == names
    assert ps[0].revealed and not ps[1].revealed
    assert ps[0].player.potential == club.prospects[0].player.potential


# --- UI headless ---
def test_cantera_ui_reveal_and_sign(monkeypatch):
    game, club = _game(monkeypatch, scouts=2)
    d = youth.intake_dates(game)[0]
    youth.run_intake(game, d, new_rng(1))

    async def run():
        app = TacticoreApp()
        async with app.run_test(size=(80, 25)) as pilot:
            app.game = game
            await app.push_screen(PlayersScreen())
            await pilot.pause()
            await pilot.press("2")   # Cantera
            await pilot.pause()
            rows = [s.text for s in app.screen._compositor.render_strips()]
            for r in rows:
                assert len(r.rstrip()) <= 80
                assert all(0x20 <= ord(c) <= 0x7E for c in r)
            assert not club.prospects[0].revealed
            await pilot.press("enter")   # revisar informe
            await pilot.pause()
            assert club.prospects[0].revealed
            before = len(club.players)
            await pilot.press("enter")   # fichar
            await pilot.pause()
            assert len(club.players) == before + 1

    asyncio.run(run())
