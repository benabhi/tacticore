"""Patrocinadores por oferta-evento: cupos, generacion, caducidad, aceptar/rechazar."""

import sqlite3
from datetime import timedelta

from tacticore import config
from tacticore.core.game import GameState
from tacticore.core.rng import new_rng
from tacticore.domain.enums import EmployeeRole, LeagueTier
from tacticore.domain.manager import Manager
from tacticore.generators import ClubGenerator, WorldGenerator
from tacticore.persistence import _db
from tacticore.simulation import daily, notifications as notif, sponsors as sp


def _game(seed, monkeypatch, countries=2):
    monkeypatch.setattr(config, "WORLD_COUNTRY_COUNT", countries)
    world = WorldGenerator(new_rng(seed)).generate()
    game = GameState.new(seed=seed, start_date=config.SEASON_START_DATE, countries=world)
    cc = world[0].code
    cg = ClubGenerator(new_rng(seed))
    club = cg.player_club(name="Mi Club", fans_name="F", stadium_name="S",
        manager=Manager("A", "B", cc), country_code=cc, members=1500,
        today=game.calendar.current_date)
    club.sponsors = [cg._sponsors.auto(club.tier)]   # firma inicial (1 cupo E)
    game.install_player_club(club)
    return game, club


def test_slots_by_tier():
    assert sp.slots_for_tier(LeagueTier.E) == 1
    assert sp.slots_for_tier(LeagueTier.A) == 5
    assert [sp.slots_for_tier(t) for t in
            (LeagueTier.E, LeagueTier.D, LeagueTier.C, LeagueTier.B, LeagueTier.A)] == [1, 2, 3, 4, 5]


def test_no_offer_when_slots_full(monkeypatch):
    game, club = _game(5, monkeypatch)
    assert sp.free_slots(club) == 0                  # E: 1 cupo, 1 firmado
    sp.tick_sponsor_offers(game, game.calendar.current_date, new_rng(5))
    assert sp._pending_offer(game) is None


def test_offer_generated_when_slot_free(monkeypatch):
    game, club = _game(5, monkeypatch)
    club.sponsors[0].weeks_remaining = 0             # contrato terminado -> cupo libre
    sp.tick_sponsor_offers(game, game.calendar.current_date, new_rng(5))
    offer = sp._pending_offer(game)
    assert offer is not None and offer.kind == notif.EVENT_SPONSOR_OFFER
    assert sp.free_slots(club) == 1                  # el terminado se limpio


def test_only_one_pending_offer_at_a_time(monkeypatch):
    game, club = _game(5, monkeypatch)
    club.sponsors[0].weeks_remaining = 0
    today = game.calendar.current_date
    sp.tick_sponsor_offers(game, today, new_rng(5))
    sp.tick_sponsor_offers(game, today, new_rng(6))
    assert sum(1 for n in notif.pending_events(game)
               if n.kind == notif.EVENT_SPONSOR_OFFER) == 1


def test_offer_expires_past_window(monkeypatch):
    game, club = _game(5, monkeypatch)
    club.sponsors[0].weeks_remaining = 0
    today = game.calendar.current_date
    sp.tick_sponsor_offers(game, today, new_rng(5))
    offer = sp._pending_offer(game)
    later = today + timedelta(days=sp._OFFER_WINDOW_DAYS + 1)
    sp.tick_sponsor_offers(game, later, new_rng(7))
    assert offer.status == "expired" and not offer.is_pending_event


def test_accept_signs_and_reject_keeps_slot(monkeypatch):
    game, club = _game(5, monkeypatch)
    club.sponsors[0].weeks_remaining = 0
    today = game.calendar.current_date
    sp.tick_sponsor_offers(game, today, new_rng(5))
    offer = sp._pending_offer(game)
    cap0 = club.capital
    assert sp.accept_offer(game, offer)
    assert len(sp.active_sponsors(club)) == 1 and offer.status == "accepted"
    assert club.capital - cap0 == offer.payload["signing_bonus"]
    assert any("Firma patrocinio" in mv.concept for mv in club.movements)

    # nueva vuelta: libero cupo, generar y rechazar -> cupo sigue libre
    club.sponsors[0].weeks_remaining = 0
    sp.tick_sponsor_offers(game, today, new_rng(9))
    o2 = sp._pending_offer(game)
    sp.reject_offer(game, o2)
    assert o2.status == "rejected" and sp.free_slots(club) == 1


def test_offer_quality_scales_with_finance_and_commercial(monkeypatch):
    from tacticore.domain.employee import Employee
    from tacticore.domain.enums import BonusType
    from datetime import date as _d
    game, club = _game(5, monkeypatch)
    base = sp.offer_quality(club)
    assert base == 1.0
    club.employees.append(Employee(role=EmployeeRole.FINANCE, first_name="N",
        last_name="N", nationality="AR", birth_date=_d(1980, 1, 1),
        bonuses={BonusType.INCOME: 100}, weekly_wage=1))
    club.facilities["shop"] = 3
    assert sp.offer_quality(club) > 1.0


def test_weekly_economy_sums_all_sponsors(monkeypatch):
    game, club = _game(5, monkeypatch)
    # dos contratos activos
    from tacticore.domain.sponsor import Sponsor, SponsorContract
    club.sponsors = [
        SponsorContract(sponsor=Sponsor("A", "s", 1), weeks_total=10, weeks_remaining=10,
                        weekly_pay=1000),
        SponsorContract(sponsor=Sponsor("B", "s", 1), weeks_total=10, weeks_remaining=5,
                        weekly_pay=500),
    ]
    friday = game.calendar.current_date
    while friday.weekday() != 4:
        friday += timedelta(days=1)
    club.movements.clear()
    daily._weekly_economy(game, friday, new_rng(1), None)
    spon_mv = next(mv for mv in club.movements if mv.concept == "Patrocinador")
    assert spon_mv.amount == 1500                     # suma de ambos
    assert [s.weeks_remaining for s in club.sponsors] == [9, 4]  # cada uno bajo


def test_round_trip_sponsors_and_events(monkeypatch):
    game, club = _game(5, monkeypatch)
    club.sponsors[0].weeks_remaining = 0
    sp.tick_sponsor_offers(game, game.calendar.current_date, new_rng(5))
    sp.accept_offer(game, sp._pending_offer(game))
    conn = sqlite3.connect(":memory:")
    _db.write_game(conn, game)
    g2 = _db.read_game(conn)
    assert len(g2.player_club.sponsors) == len(club.sponsors)
    assert any(n.status == "accepted" and n.kind == notif.EVENT_SPONSOR_OFFER
               for n in g2.notifications)
