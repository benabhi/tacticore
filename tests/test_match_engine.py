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
    # El saque del medio es determinista (un pase); la divergencia viene del azar
    # del juego (errores de pase, quites, atajadas). Tras un rato, difieren.
    a = MatchEngine(_fresh_state(), new_rng(1))
    b = MatchEngine(_fresh_state(), new_rng(2))
    a.run(8.0)
    b.run(8.0)
    pa = [(mp.position.x, mp.position.y) for mp in a.state.all_players()]
    pb = [(mp.position.x, mp.position.y) for mp in b.state.all_players()]
    assert pa != pb


def test_kickoff_sets_ball_moving_and_phase():
    engine = MatchEngine(_fresh_state(), new_rng(3))
    assert engine.state.phase is MatchPhase.KICKOFF
    engine.run(12.0)  # pasa el delay pre-partido y se saca del medio
    assert engine.state.phase is MatchPhase.PLAYING  # ya se jugo (saco del medio)
    assert any(e.kind == "pase" for e in engine.state.log)  # el saque puso la pelota en juego


def test_ball_stays_inside_pitch():
    engine = MatchEngine(_fresh_state(), new_rng(5))
    engine.run(15.0)
    assert engine.state.pitch.contains(engine.state.ball.position)


def test_clock_advances():
    engine = MatchEngine(_fresh_state(), new_rng(9))
    engine.run(1.0, DEFAULT_DT)
    assert abs(engine.state.clock - 1.0) < 1e-6
