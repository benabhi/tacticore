"""Forma por participacion: sube al jugar el partido de liga, baja al no jugar."""

from tacticore import config
from tacticore.core.game import GameState
from tacticore.core.rng import new_rng
from tacticore.domain.enums import MatchKind
from tacticore.domain.manager import Manager
from tacticore.domain.match import Match
from tacticore.domain.tactic import Tactic
from tacticore.generators import ClubGenerator, WorldGenerator
from tacticore.simulation import form


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
    return game, club


def _league_match(game, club, gf, ga, lineup):
    rival = next(c for c in game.player_league.clubs if c is not club)
    return Match(home=club, away=rival, kind=MatchKind.LEAGUE,
                 home_goals=gf, away_goals=ga, played=True,
                 tactic=Tactic(formation="4-3-3", lineup=list(lineup)))


def test_form_up_for_players_down_for_bench(monkeypatch):
    game, club = _game(monkeypatch)
    for p in club.players:
        p.form = 50.0
    lineup = club.players[:11]
    bench = club.players[11:]
    form.update_after_match(game, _league_match(game, club, 2, 1, lineup))  # victoria
    assert all(p.form == 50.0 + form.FORM_PLAYED + form.FORM_WIN for p in lineup)
    assert all(p.form == 50.0 - form.FORM_BENCH for p in bench)


def test_form_win_bonus_only_on_win(monkeypatch):
    game, club = _game(monkeypatch)
    for p in club.players:
        p.form = 50.0
    lineup = club.players[:11]
    form.update_after_match(game, _league_match(game, club, 0, 1, lineup))  # derrota
    assert all(p.form == 50.0 + form.FORM_PLAYED for p in lineup)   # sin extra


def test_form_clamped_1_100(monkeypatch):
    game, club = _game(monkeypatch)
    lineup = club.players[:11]
    for p in lineup:
        p.form = 99.0
    for p in club.players[11:]:
        p.form = 2.0
    form.update_after_match(game, _league_match(game, club, 3, 0, lineup))
    assert all(p.form <= 100.0 for p in lineup)
    assert all(1.0 <= p.form for p in club.players[11:])


def test_form_uses_top11_when_no_tactic(monkeypatch):
    game, club = _game(monkeypatch)
    for p in club.players:
        p.form = 50.0
    top11 = sorted(club.players, key=lambda p: p.overall, reverse=True)[:11]
    rival = next(c for c in game.player_league.clubs if c is not club)
    m = Match(home=club, away=rival, kind=MatchKind.LEAGUE,
              home_goals=1, away_goals=1, played=True, tactic=None)  # sin tactica
    form.update_after_match(game, m)
    assert all(p.form > 50.0 for p in top11)                # los 11 mejores "jugaron"
    others = [p for p in club.players if p not in top11]
    assert all(p.form < 50.0 for p in others)


def test_finish_player_match_moves_form_only_on_league(monkeypatch):
    from tacticore.simulation.daily import finish_player_match
    game, club = _game(monkeypatch)
    for p in club.players:
        p.form = 50.0
    rival = next(c for c in game.player_league.clubs if c is not club)
    # Amistoso: NO mueve la forma.
    friendly = Match(home=club, away=rival, kind=MatchKind.FRIENDLY,
                     tactic=Tactic(formation="4-3-3", lineup=list(club.players[:11])))
    finish_player_match(game, friendly, 2, 0)
    assert all(p.form == 50.0 for p in club.players)
    # Liga: SI mueve la forma.
    league = Match(home=club, away=rival, kind=MatchKind.LEAGUE,
                   tactic=Tactic(formation="4-3-3", lineup=list(club.players[:11])))
    finish_player_match(game, league, 2, 0)
    assert club.players[0].form > 50.0
