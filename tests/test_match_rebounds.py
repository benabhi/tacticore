"""Tests de atajadas y rebotes del arquero (G5)."""

from tacticore.core.rng import new_rng
from tacticore.domain.enums import LeagueTier
from tacticore.generators import ClubGenerator
from tacticore.simulation.match import MatchEngine, Vec2, kickoff_state
from tacticore.simulation.match import ai


def _state():
    gen = ClubGenerator(new_rng(42))
    home = gen.generate(squad_size=16, country_code="AR", tier=LeagueTier.C)
    away = gen.generate(squad_size=16, country_code="BR", tier=LeagueTier.C)
    return kickoff_state(home, away)


class _FakeRng:
    def __init__(self, values):
        self._values = list(values)
        self._i = 0

    def random(self):
        v = self._values[self._i % len(self._values)]
        self._i += 1
        return v

    def uniform(self, a, b):
        return (a + b) / 2.0


def _keeper(state, side_players):
    return next(mp for mp in side_players if ai.is_goalkeeper(mp))


def test_good_hands_hold_the_shot():
    engine = MatchEngine(_state(), new_rng(1))
    engine._rng = _FakeRng([0.9, 0.0])  # no la tira al corner; random < p_hold -> retiene
    st = engine.state
    gk = _keeper(st, st.away)
    gk.player.composure = 100.0
    st.ball.position = gk.position
    st.ball.velocity = Vec2(-20.0, 0.0)
    st.ball.owner = None
    engine._goalkeeper_save(gk)
    assert st.ball.owner is gk
    assert st.last_event == "Atajada"


def test_keeper_can_tip_the_shot_for_a_corner():
    engine = MatchEngine(_state(), new_rng(1))
    engine._rng = _FakeRng([0.0])  # primer roll < p_corner -> manotazo al corner
    st = engine.state
    from tacticore.simulation.match import Side
    gk = _keeper(st, st.away)       # AWAY defiende x = length
    st.ball.position = gk.position
    st.ball.velocity = Vec2(20.0, 0.0)
    st.ball.owner = None
    engine._goalkeeper_save(gk)
    assert engine._restart_kind == "corner"      # se concede un corner
    assert engine._restart_side is Side.HOME      # para el rival del arquero
    assert st.ball.position.x > st.pitch.length - 1.0  # saque desde la esquina del fondo


def test_poor_hands_can_spill_a_rebound():
    engine = MatchEngine(_state(), new_rng(1))
    engine._rng = _FakeRng([0.99])  # random >= p_hold -> rebote
    st = engine.state
    gk = _keeper(st, st.away)
    gk.player.composure = 30.0
    st.ball.position = gk.position
    st.ball.velocity = Vec2(-20.0, 0.0)
    st.ball.owner = None
    engine._goalkeeper_save(gk)
    assert st.ball.owner is None        # queda viva
    assert st.ball.velocity.length() > 0.0
    assert st.last_event == "Rebote"


def test_rebound_goes_away_from_own_goal():
    engine = MatchEngine(_state(), new_rng(1))
    engine._rng = _FakeRng([0.99])
    st = engine.state
    gk = _keeper(st, st.away)  # AWAY defiende el arco en x = length
    gk.player.composure = 20.0
    st.ball.position = gk.position
    st.ball.velocity = Vec2(20.0, 0.0)
    st.ball.owner = None
    engine._goalkeeper_save(gk)
    # El rebote sale alejandose del arco propio (hacia el centro: x decreciente).
    assert st.ball.velocity.x < 0.0


def test_better_composure_holds_more():
    def holds_with(composure):
        held = 0
        for seed in range(60):
            engine = MatchEngine(_state(), new_rng(seed))
            st = engine.state
            gk = _keeper(st, st.away)
            gk.player.composure = composure
            st.ball.position = gk.position
            st.ball.velocity = Vec2(-20.0, 0.0)
            st.ball.owner = None
            engine._goalkeeper_save(gk)
            if st.ball.owner is gk:
                held += 1
        return held

    assert holds_with(95.0) > holds_with(20.0)


def test_rebounds_are_deterministic():
    a = MatchEngine(_state(), new_rng(7))
    b = MatchEngine(_state(), new_rng(7))
    a.run(8.0)
    b.run(8.0)
    assert a.state.ball.position == b.state.ball.position
