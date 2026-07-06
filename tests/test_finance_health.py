"""Salud financiera: ventas forzadas, descenso por quiebra, premio por ascenso, parcelas."""

from tacticore import config
from tacticore.core.game import GameState
from tacticore.core.rng import new_rng
from tacticore.domain.enums import LeagueTier
from tacticore.domain.manager import Manager
from tacticore.domain.sponsor import Sponsor, SponsorContract
from tacticore.generators import ClubGenerator, WorldGenerator
from tacticore.simulation import facilities as fac
from tacticore.simulation import finance_health as fh
from tacticore.simulation import promotion
from tacticore.simulation.economy import player_value
from tacticore.simulation.transfers import MIN_SQUAD

_TIER_ORDER = list(LeagueTier)


def _game(seed, monkeypatch, countries=2):
    monkeypatch.setattr(config, "WORLD_COUNTRY_COUNT", countries)
    world = WorldGenerator(new_rng(seed)).generate()
    game = GameState.new(seed=seed, start_date=config.SEASON_START_DATE, countries=world)
    cc = world[0].code
    club = ClubGenerator(new_rng(seed)).player_club(
        name="Mi Club", fans_name="F", stadium_name="S",
        manager=Manager("A", "B", cc), country_code=cc,
        today=game.calendar.current_date)
    game.install_player_club(club)
    return game, club


def _move_player_to(game, tier):
    """Mueve al jugador a `tier` intercambiando con un club de esa liga (mantiene 8)."""
    club = game.player_club
    src = game.player_league
    dest = next(lg for lg in game.player_country.leagues if lg.tier is tier)
    victim = dest.clubs[0]
    src.clubs.remove(club); dest.clubs.append(club); club.tier = tier
    dest.clubs.remove(victim); src.clubs.append(victim); victim.tier = src.tier


def test_starts_with_zero_plots(monkeypatch):
    _, club = _game(11, monkeypatch)
    assert club.plots == 0
    # con 0 parcelas, la primera cuesta el base del tier (E)
    assert fac.plot_cost(club) == 15_000


def test_forced_sale_recovers_when_shallow(monkeypatch):
    game, club = _game(11, monkeypatch)
    today = game.calendar.current_date
    cheapest = min(player_value(p, today) for p in club.players)
    club.capital = -(cheapest // 2)          # deuda chica: 1 venta alcanza
    squad0 = len(club.players)
    fh.enforce_solvency(game, today)
    assert club.capital >= 0                  # recupero
    assert len(club.players) < squad0         # vendio al menos uno
    assert any("Venta forzada" in mv.concept for mv in club.movements)
    assert any(n.subject == "Ventas forzadas por deuda" for n in game.notifications)


def test_forced_sale_stops_at_min_squad(monkeypatch):
    game, club = _game(11, monkeypatch)
    today = game.calendar.current_date
    club.capital = -5_000_000                 # deuda enorme: no se cubre vendiendo
    fh.enforce_solvency(game, today)
    assert len(club.players) == MIN_SQUAD     # vendio hasta el minimo y freno
    assert club.capital < 0                   # sigue en rojo


def test_solvent_club_sells_nothing(monkeypatch):
    game, club = _game(11, monkeypatch)
    club.capital = 50_000
    squad0 = len(club.players)
    fh.enforce_solvency(game, game.calendar.current_date)
    assert len(club.players) == squad0 and club.capital == 50_000


def test_forced_relegation_when_insolvent(monkeypatch):
    game, club = _game(11, monkeypatch)
    _move_player_to(game, LeagueTier.D)
    club.capital = -1
    promotion._force_relegate_if_insolvent(game)
    assert club.tier is LeagueTier.E                       # bajo un tier
    assert club in next(lg for lg in game.player_country.leagues
                        if lg.tier is LeagueTier.E).clubs
    # se mantiene el tamano de ambas ligas (swap 1 a 1)
    for lg in game.player_country.leagues:
        assert len(lg.clubs) == 8
    assert any(n.subject == "Descenso por quiebra" for n in game.notifications)


def test_no_relegation_below_E(monkeypatch):
    game, club = _game(11, monkeypatch)   # arranca en E
    club.capital = -1
    promotion._force_relegate_if_insolvent(game)
    assert club.tier is LeagueTier.E
    assert any(n.subject == "Alerta de quiebra" for n in game.notifications)


def test_promotion_bonus_credited_on_ascent(monkeypatch):
    game, club = _game(11, monkeypatch)
    club.sponsor = SponsorContract(
        sponsor=Sponsor(name="X", sector="Y", tier=1),
        weeks_total=52, weeks_remaining=40, weekly_pay=500,
        signing_bonus=0, promotion_bonus=50_000)
    # simular que venia de E y ahora esta en D (ascendio)
    club.tier = LeagueTier.D
    cap0 = club.capital
    promotion._credit_promotion_bonus(game, before=(LeagueTier.E, 1, 8))
    assert club.capital == cap0 + 50_000
    assert any(n.subject == "Premio por ascenso" for n in game.notifications)


def test_promotion_bonus_not_credited_without_ascent(monkeypatch):
    game, club = _game(11, monkeypatch)
    club.sponsor = SponsorContract(
        sponsor=Sponsor(name="X", sector="Y", tier=1),
        weeks_total=52, weeks_remaining=40, weekly_pay=500,
        signing_bonus=0, promotion_bonus=50_000)
    cap0 = club.capital  # sigue en E (before == E, actual == E: no ascendio)
    promotion._credit_promotion_bonus(game, before=(LeagueTier.E, 4, 8))
    assert club.capital == cap0
