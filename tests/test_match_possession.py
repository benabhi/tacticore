"""Tests de posesion y pase/remate (B3.2)."""

from tacticore.core.rng import new_rng
from tacticore.domain.enums import LeagueTier, Position
from tacticore.generators import ClubGenerator
from tacticore.simulation.match import DEFAULT_DT, MatchEngine, kickoff_state
from tacticore.simulation.match import ai


def _fresh_state():
    gen = ClubGenerator(new_rng(42))
    home = gen.generate(squad_size=16, country_code="AR", tier=LeagueTier.C)
    away = gen.generate(squad_size=16, country_code="BR", tier=LeagueTier.C)
    return kickoff_state(home, away)


def test_possession_is_gained():
    engine = MatchEngine(_fresh_state(), new_rng(1))
    gained = False
    for _ in range(int(8.0 / DEFAULT_DT)):
        engine.step()
        if engine.state.ball.owner is not None:
            gained = True
            break
    assert gained, "alguien deberia haber dominado la pelota"


def test_ball_circulates():
    state = _fresh_state()
    center = state.pitch.center
    engine = MatchEngine(state, new_rng(1))
    engine.run(10.0)
    # La pelota se movio del centro (hubo juego).
    assert engine.state.ball.position.distance_to(center) > 3.0


def test_owned_ball_follows_carrier():
    engine = MatchEngine(_fresh_state(), new_rng(1))
    for _ in range(int(8.0 / DEFAULT_DT)):
        engine.step()
        owner = engine.state.ball.owner
        if owner is not None:
            # La pelota esta pegada al que la lleva.
            assert engine.state.ball.position.distance_to(owner.position) < 1.0
            break


def test_pass_target_is_a_teammate():
    state = _fresh_state()
    owner = next(p for p in state.home if p.player.position is Position.MIDFIELDER)
    target = ai.best_pass_target(owner, state, max_dist=60.0)
    if target is not None:
        assert target in state.home
        assert target is not owner


def test_possession_is_deterministic():
    a = MatchEngine(_fresh_state(), new_rng(1))
    b = MatchEngine(_fresh_state(), new_rng(1))
    a.run(6.0)
    b.run(6.0)
    assert a.state.ball.position == b.state.ball.position
    assert (a.state.ball.owner is None) == (b.state.ball.owner is None)
