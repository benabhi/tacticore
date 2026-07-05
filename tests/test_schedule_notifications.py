"""Calendario nuevo (liga domingo / amistoso miercoles) + notificaciones y libro
de caja del club del jugador."""

from datetime import timedelta

from tacticore import config
from tacticore.core.game import GameState
from tacticore.core.rng import new_rng
from tacticore.domain.enums import MatchKind
from tacticore.domain.manager import Manager
from tacticore.generators import ClubGenerator, WorldGenerator
from tacticore.simulation.daily import advance_day, player_match_on
from tacticore.simulation.notifications import unread_count
from tacticore.simulation.season import ensure_all_fixtures, ensure_player_friendlies


def _game(seed: int, monkeypatch):
    monkeypatch.setattr(config, "WORLD_COUNTRY_COUNT", 3)
    world = WorldGenerator(new_rng(seed)).generate()
    game = GameState.new(seed=seed, start_date=config.SEASON_START_DATE, countries=world)
    cc = world[0].code
    club = ClubGenerator(new_rng(seed)).player_club(
        name="Mi Club", fans_name="F", stadium_name="Estadio S",
        manager=Manager("A", "B", cc), country_code=cc,
        today=game.calendar.current_date)
    game.install_player_club(club)
    ensure_all_fixtures(game)
    ensure_player_friendlies(game)
    return game, club


def test_league_on_sunday_friendlies_on_wednesday(monkeypatch):
    game, club = _game(11, monkeypatch)
    league = game.player_league
    for m in league.matches:
        assert m.match_date.weekday() == 6  # domingo
    assert game.friendlies, "deberia haber amistosos"
    for f in game.friendlies:
        assert f.match_date.weekday() == 2  # miercoles
        assert f.kind is MatchKind.FRIENDLY
        rival = f.away if f.home is club else f.home
        assert rival.country_code != club.country_code  # otro pais
        assert rival.tier is club.tier                  # mismo nivel


def test_friendly_is_a_player_match_on_its_wednesday(monkeypatch):
    game, club = _game(11, monkeypatch)
    fr = game.friendlies[0]
    # avanzar hasta ese miercoles sin jugarlo (skip)
    while game.calendar.current_date < fr.match_date:
        advance_day(game, skip_player_match=True)
    found = player_match_on(game, fr.match_date)
    assert found is fr and not fr.played


def test_weekly_close_notifies_and_logs_movements(monkeypatch):
    game, club = _game(11, monkeypatch)
    # avanzar hasta pasar el primer viernes (cierre economico)
    for _ in range(8):
        advance_day(game)
    assert any(n.category == "finanzas" for n in game.notifications), \
        "el cierre economico deberia notificar"
    assert unread_count(game) == len(game.notifications)  # nada leido aun
    # el club del jugador llevo libro (al menos sueldos y socios)
    concepts = {mv.concept for mv in club.movements}
    assert "Sueldos" in concepts and "Cuota de socios" in concepts


def test_home_match_credits_gate_as_movement(monkeypatch):
    """Tras jugar de local, la taquilla aparece como movimiento (tiempo real)."""
    game, club = _game(11, monkeypatch)
    # jugar una temporada headless: en algun momento el jugador es local
    for _ in range(40):
        advance_day(game)
    gate = [mv for mv in club.movements if mv.concept.startswith("Taquilla")]
    assert gate and all(mv.amount > 0 for mv in gate)
