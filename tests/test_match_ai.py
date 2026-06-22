"""Tests de la IA del partido (steering, persecucion de la pelota)."""

from tacticore.core.rng import new_rng
from tacticore.domain.enums import LeagueTier
from tacticore.generators import ClubGenerator
from tacticore.simulation.match import MatchEngine, Side, kickoff_state
from tacticore.simulation.match import ai
from tacticore.simulation.match.geometry import Vec2


def _fresh_state():
    gen = ClubGenerator(new_rng(42))
    home = gen.generate(squad_size=16, country_code="AR", tier=LeagueTier.C)
    away = gen.generate(squad_size=16, country_code="BR", tier=LeagueTier.C)
    return kickoff_state(home, away)


def test_max_speed_grows_with_attribute():
    import copy

    base = _fresh_state().home[0].player
    slow = copy.copy(base)
    slow.speed = 10.0
    fast = copy.copy(base)
    fast.speed = 90.0
    assert ai.max_speed(fast) > ai.max_speed(slow)


def test_arrive_slows_near_target():
    origin = Vec2(0.0, 0.0)
    far = ai.arrive(origin, Vec2(50.0, 0.0), top_speed=8.0)
    near = ai.arrive(origin, Vec2(1.0, 0.0), top_speed=8.0)  # dentro del slow radius
    assert abs(far.length() - 8.0) < 1e-6
    assert near.length() < 8.0


def test_a_chaser_reaches_the_ball():
    engine = MatchEngine(_fresh_state(), new_rng(1))
    engine.run(6.0)
    ball = engine.state.ball.position
    nearest = min(
        engine.state.all_players(),
        key=lambda mp: mp.position.distance_to(ball),
    )
    # Alguien llego (practicamente) a la pelota.
    assert nearest.position.distance_to(ball) < 1.5


def test_chasers_move_others_hold():
    state = _fresh_state()
    bases = {id(mp): mp.base_position for mp in state.all_players()}
    chaser = ai.team_ball_chaser(state, Side.HOME)
    chaser_start = chaser.position
    engine = MatchEngine(state, new_rng(1))
    engine.run(4.0)
    # El perseguidor se movio de su base.
    assert chaser.position.distance_to(chaser_start) > 1.0
    # Un jugador lejano (que no persigue) sigue cerca de su base.
    holders = [
        mp for mp in engine.state.home
        if mp.position.distance_to(bases[id(mp)]) < 0.5
    ]
    assert holders, "deberia haber jugadores sosteniendo su posicion"


def test_ai_is_deterministic():
    a = MatchEngine(_fresh_state(), new_rng(1))
    b = MatchEngine(_fresh_state(), new_rng(1))
    a.run(5.0)
    b.run(5.0)
    pa = [(mp.position.x, mp.position.y) for mp in a.state.all_players()]
    pb = [(mp.position.x, mp.position.y) for mp in b.state.all_players()]
    assert pa == pb
