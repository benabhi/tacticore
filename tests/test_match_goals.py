"""Tests de goles, saque tras gol y arquero (B3.3)."""

from tacticore.core.rng import new_rng
from tacticore.domain.enums import LeagueTier
from tacticore.generators import ClubGenerator
from tacticore.simulation.match import (
    MatchEngine,
    MatchPhase,
    Vec2,
    kickoff_state,
)
from tacticore.simulation.match import ai


def _fresh_state():
    gen = ClubGenerator(new_rng(42))
    home = gen.generate(squad_size=16, country_code="AR", tier=LeagueTier.C)
    away = gen.generate(squad_size=16, country_code="BR", tier=LeagueTier.C)
    return kickoff_state(home, away)


def test_home_goal_is_scored_and_kickoff_restarts():
    state = _fresh_state()
    state.phase = MatchPhase.PLAYING  # evita que el primer step saque del medio
    state.ball.owner = None
    state.ball.position = Vec2(state.pitch.length - 0.1, state.pitch.width / 2)
    state.ball.velocity = Vec2(10.0, 0.0)
    engine = MatchEngine(state, new_rng(1))
    engine.step()
    assert state.score_home == 1
    assert state.score_away == 0
    assert state.phase is MatchPhase.KICKOFF
    assert state.ball.position == state.pitch.center
    assert state.ball.owner is None


def test_away_can_score():
    state = _fresh_state()
    state.phase = MatchPhase.PLAYING
    state.ball.owner = None
    state.ball.position = Vec2(0.1, state.pitch.width / 2)
    state.ball.velocity = Vec2(-10.0, 0.0)
    engine = MatchEngine(state, new_rng(1))
    engine.step()
    assert state.score_away == 1
    assert state.score_home == 0


def test_shot_wide_is_no_goal():
    state = _fresh_state()
    state.phase = MatchPhase.PLAYING
    state.ball.owner = None
    # Cerca del banderin del corner, fuera de la boca del arco.
    state.ball.position = Vec2(state.pitch.length - 0.1, 5.0)
    state.ball.velocity = Vec2(10.0, 0.0)
    engine = MatchEngine(state, new_rng(1))
    engine.step()
    assert state.score_home == 0
    assert state.phase is MatchPhase.PLAYING


def test_goalkeeper_clears_instead_of_dribbling():
    state = _fresh_state()
    gk = next(mp for mp in state.home if ai.is_goalkeeper(mp))
    state.phase = MatchPhase.PLAYING
    state.ball.owner = gk
    state.ball.position = gk.position
    engine = MatchEngine(state, new_rng(1))
    engine.step()
    # Tras el despeje la pelota queda suelta y viajando.
    assert state.ball.owner is None
    assert state.ball.velocity.length() > 0.0


def test_goalkeeper_stays_near_its_goal():
    state = _fresh_state()
    gk = next(mp for mp in state.home if ai.is_goalkeeper(mp))
    engine = MatchEngine(state, new_rng(3))
    engine.run(20.0)
    # El arquero local no se va de su arco (x pequeno).
    assert gk.position.x < 20.0


def test_goals_are_deterministic():
    a = MatchEngine(_fresh_state(), new_rng(7))
    b = MatchEngine(_fresh_state(), new_rng(7))
    a.run(30.0)
    b.run(30.0)
    assert (a.state.score_home, a.state.score_away) == (
        b.state.score_home,
        b.state.score_away,
    )
    assert a.state.ball.position == b.state.ball.position
