"""Tests del armado del estado inicial del partido (saque del medio)."""

from tacticore.core.rng import new_rng
from tacticore.domain.enums import LeagueTier, Position
from tacticore.generators import ClubGenerator
from tacticore.simulation.match import Side, kickoff_state
from tacticore.simulation.match.formation import DEFAULT_FORMATIONS


def _two_clubs():
    gen = ClubGenerator(new_rng(42))
    home = gen.generate(squad_size=16, country_code="AR", tier=LeagueTier.C)
    away = gen.generate(squad_size=16, country_code="BR", tier=LeagueTier.C)
    return home, away


def test_kickoff_has_full_teams_and_ball_centered():
    home, away = _two_clubs()
    state = kickoff_state(home, away)
    size = DEFAULT_FORMATIONS[11].size  # el juego arranca 11v11
    assert size == 11
    assert len(state.home) == size
    assert len(state.away) == size
    assert state.ball.position == state.pitch.center


def test_all_players_inside_pitch():
    home, away = _two_clubs()
    state = kickoff_state(home, away)
    for mp in state.all_players():
        assert state.pitch.contains(mp.position)
        # En el saque, posicion y ancla de formacion coinciden.
        assert mp.position == mp.base_position


def test_goalkeepers_on_opposite_ends():
    home, away = _two_clubs()
    state = kickoff_state(home, away)
    home_gk = next(p for p in state.home if p.player.position is Position.GOALKEEPER)
    away_gk = next(p for p in state.away if p.player.position is Position.GOALKEEPER)
    # El arquero local cerca de x=0; el visitante cerca de x=length.
    assert home_gk.position.x < state.pitch.length / 2
    assert away_gk.position.x > state.pitch.length / 2


def test_teams_are_mirrored():
    # Misma formacion espejada: para cada slot, home.x + away.x == length.
    home, away = _two_clubs()
    state = kickoff_state(home, away)
    for hp, ap in zip(state.home, state.away):
        assert abs((hp.position.x + ap.position.x) - state.pitch.length) < 1e-9
        assert hp.position.y == ap.position.y
    assert state.home[0].team is Side.HOME
    assert state.away[0].team is Side.AWAY
