"""Tests del tick del motor de partido (determinismo, fisica basica)."""

from tacticore.core.rng import new_rng
from tacticore.domain.enums import LeagueTier
from tacticore.generators import ClubGenerator
from tacticore.simulation.match import (
    DEFAULT_DT,
    MatchEngine,
    MatchPhase,
    kickoff_state,
)


def _fresh_state():
    gen = ClubGenerator(new_rng(42))
    home = gen.generate(squad_size=16, country_code="AR", tier=LeagueTier.C)
    away = gen.generate(squad_size=16, country_code="BR", tier=LeagueTier.C)
    return kickoff_state(home, away)


def test_same_seed_is_deterministic():
    a = MatchEngine(_fresh_state(), new_rng(1))
    b = MatchEngine(_fresh_state(), new_rng(1))
    a.run(2.0)
    b.run(2.0)
    assert a.state.ball.position == b.state.ball.position
    assert a.state.ball.velocity == b.state.ball.velocity


def test_different_seed_diverges():
    a = MatchEngine(_fresh_state(), new_rng(1))
    b = MatchEngine(_fresh_state(), new_rng(2))
    a.step()  # el saque usa el rng -> distinta direccion
    b.step()
    assert a.state.ball.velocity != b.state.ball.velocity


def test_kickoff_sets_ball_moving_and_phase():
    engine = MatchEngine(_fresh_state(), new_rng(3))
    assert engine.state.phase is MatchPhase.KICKOFF
    engine.step()
    assert engine.state.phase is MatchPhase.PLAYING
    assert engine.state.ball.velocity.length() > 0.0


def test_ball_stops_and_stays_inside():
    engine = MatchEngine(_fresh_state(), new_rng(5))
    engine.run(15.0)  # tiempo de sobra para que se frene
    assert engine.state.ball.velocity.length() < 0.01
    assert engine.state.pitch.contains(engine.state.ball.position)


def test_players_stay_still_without_ai():
    state = _fresh_state()
    before = [(mp.position.x, mp.position.y) for mp in state.all_players()]
    engine = MatchEngine(state, new_rng(7))
    engine.run(3.0)
    after = [(mp.position.x, mp.position.y) for mp in engine.state.all_players()]
    assert before == after  # sin IA, nadie se mueve


def test_clock_advances():
    engine = MatchEngine(_fresh_state(), new_rng(9))
    engine.run(1.0, DEFAULT_DT)
    assert abs(engine.state.clock - 1.0) < 1e-6
