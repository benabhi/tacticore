"""Tests de desmarques: movimiento off-ball del ataque (G3.x)."""

from tacticore.core.rng import new_rng
from tacticore.domain.enums import LeagueTier
from tacticore.generators import ClubGenerator
from tacticore.simulation.match import (
    DEFAULT_DT,
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


def test_run_target_is_ahead_of_base():
    st = _fresh_state()
    attacker = st.home[6]  # HOME ataca el arco en x = length
    goal = st.pitch.away_goal
    target = ai.attacking_run_target(attacker, st)
    # El desmarque queda mas cerca del arco rival que su ancla de formacion.
    assert target.distance_to(goal) < attacker.base_position.distance_to(goal)


def test_work_rate_makes_longer_runs():
    st = _fresh_state()
    attacker = st.home[6]
    # Aislamos: rivales lejos para que no haya correccion por espacio.
    for o in st.away:
        o.position = Vec2(0.0, 0.0)
    base = attacker.base_position
    attacker.player.work_rate = 95.0
    long_run = ai.attacking_run_target(attacker, st).distance_to(base)
    attacker.player.work_rate = 10.0
    short_run = ai.attacking_run_target(attacker, st).distance_to(base)
    assert long_run > short_run


def test_attacker_moves_off_the_ball_during_possession():
    st = _fresh_state()
    st.phase = MatchPhase.PLAYING
    owner = st.home[4]
    st.ball.owner = owner
    st.ball.position = owner.position
    attacker = st.home[6]
    base = attacker.base_position
    engine = MatchEngine(st, new_rng(1))
    max_moved = 0.0
    for _ in range(int(2.0 / DEFAULT_DT)):
        engine.step()
        max_moved = max(max_moved, attacker.position.distance_to(base))
    assert max_moved > 1.0


def test_runs_are_deterministic():
    a = MatchEngine(_fresh_state(), new_rng(7))
    b = MatchEngine(_fresh_state(), new_rng(7))
    a.run(5.0)
    b.run(5.0)
    pa = [(mp.position.x, mp.position.y) for mp in a.state.all_players()]
    pb = [(mp.position.x, mp.position.y) for mp in b.state.all_players()]
    assert pa == pb
