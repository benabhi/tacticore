"""Tests de pases cortos/largos y error segun atributos (G3)."""

import statistics

from tacticore.core.rng import new_rng
from tacticore.domain.enums import LeagueTier
from tacticore.generators import ClubGenerator
from tacticore.simulation.match import MatchEngine, Vec2, kickoff_state
from tacticore.simulation.match import ai


def _fresh_state():
    gen = ClubGenerator(new_rng(42))
    home = gen.generate(squad_size=16, country_code="AR", tier=LeagueTier.C)
    away = gen.generate(squad_size=16, country_code="BR", tier=LeagueTier.C)
    return kickoff_state(home, away)


def test_pick_pass_prefers_the_open_mate():
    st = _fresh_state()
    owner = st.home[4]
    open_mate = st.home[6]
    covered = st.home[5]
    open_mate.position = owner.position + Vec2(8.0, 0.0)
    covered.position = owner.position + Vec2(8.0, 3.0)
    # Aislamos: el resto de companeros fuera de alcance (queremos solo estos dos).
    for m in st.home:
        if m not in (owner, open_mate, covered):
            m.position = Vec2(0.0, 0.0)
    # Alejamos a los rivales y pegamos uno solo al companero "cubierto".
    for o in st.away:
        o.position = Vec2(0.0, 0.0)
    st.away[0].position = covered.position + Vec2(0.5, 0.0)
    pick = ai.pick_pass(owner, st, 40.0)
    assert pick is not None
    assert pick[0] is open_mate


def test_vision_enables_the_long_ball():
    st = _fresh_state()
    owner = st.home[4]
    for o in st.away:
        o.position = Vec2(0.0, 0.0)
    long_mate = st.home[6]
    long_mate.position = owner.position + Vec2(25.0, 0.0)   # largo y adelantado
    short_mate = st.home[5]
    short_mate.position = owner.position + Vec2(6.0, 8.0)   # corto y seguro

    owner.player.vision = 95.0
    pick_hi = ai.pick_pass(owner, st, 40.0)
    owner.player.vision = 10.0
    pick_lo = ai.pick_pass(owner, st, 40.0)

    assert pick_hi == (long_mate, True)    # con vision juega el largo
    assert pick_lo[0] is short_mate        # sin vision, no arriesga


def test_perfect_passer_has_no_error():
    engine = MatchEngine(_fresh_state(), new_rng(1))
    p = engine.state.home[3].player
    p.passing = 100.0
    assert engine._pass_error(p, is_long=False) == Vec2(0.0, 0.0)
    assert engine._pass_error(p, is_long=True) == Vec2(0.0, 0.0)


def test_worse_passer_deviates_more():
    engine = MatchEngine(_fresh_state(), new_rng(5))
    good = engine.state.home[3].player
    good.passing = 95.0
    bad = engine.state.home[4].player
    bad.passing = 20.0
    eg = statistics.mean(engine._pass_error(good, False).length() for _ in range(300))
    eb = statistics.mean(engine._pass_error(bad, False).length() for _ in range(300))
    assert eb > eg


def test_long_pass_deviates_more_than_short():
    engine = MatchEngine(_fresh_state(), new_rng(5))
    p = engine.state.home[3].player
    p.passing = 50.0
    short = statistics.mean(engine._pass_error(p, False).length() for _ in range(300))
    lng = statistics.mean(engine._pass_error(p, True).length() for _ in range(300))
    assert lng > short


def test_passing_is_deterministic():
    a = MatchEngine(_fresh_state(), new_rng(7))
    b = MatchEngine(_fresh_state(), new_rng(7))
    a.run(6.0)
    b.run(6.0)
    assert a.state.ball.position == b.state.ball.position
