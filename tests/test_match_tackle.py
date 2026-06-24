"""Tests de quite, faltas y tiros libres (G4)."""

from tacticore.core.rng import new_rng
from tacticore.domain.enums import LeagueTier
from tacticore.generators import ClubGenerator
from tacticore.simulation.match import (
    MatchEngine,
    MatchPhase,
    Side,
    Vec2,
    kickoff_state,
)


def _state():
    gen = ClubGenerator(new_rng(42))
    home = gen.generate(squad_size=16, country_code="AR", tier=LeagueTier.C)
    away = gen.generate(squad_size=16, country_code="BR", tier=LeagueTier.C)
    st = kickoff_state(home, away)
    st.phase = MatchPhase.PLAYING
    return st


class _FakeRng:
    """Rng de prueba: devuelve valores fijos en orden."""

    def __init__(self, values):
        self._values = list(values)
        self._i = 0

    def random(self):
        v = self._values[self._i % len(self._values)]
        self._i += 1
        return v


def test_clean_tackle_wins_possession():
    engine = MatchEngine(_state(), new_rng(1))
    engine._rng = _FakeRng([0.0])  # random < p_win -> gana el quite
    st = engine.state
    carrier = st.home[6]
    st.ball.owner = carrier
    st.ball.position = carrier.position
    defender = st.away[1]
    engine._attempt_tackle(defender, carrier)
    assert st.ball.owner is defender
    assert st.last_event == "Quite"


def test_failed_tackle_can_be_a_foul():
    engine = MatchEngine(_state(), new_rng(1))
    engine._rng = _FakeRng([0.99, 0.0])  # falla el quite y es falta
    st = engine.state
    carrier = st.home[6]
    carrier.position = Vec2(50.0, 34.0)  # mediocampo, fuera de cualquier area
    st.ball.owner = carrier
    st.ball.position = carrier.position
    defender = st.away[1]
    engine._attempt_tackle(defender, carrier)
    assert st.last_event == "Tiro libre"
    assert st.ball.owner is None
    assert engine._restart_side is Side.HOME  # saque para el equipo del que sufrio


def test_foul_inside_the_box_is_a_penalty():
    engine = MatchEngine(_state(), new_rng(1))
    engine._rng = _FakeRng([0.99, 0.0])
    st = engine.state
    carrier = st.home[6]  # HOME ataca el arco en x = length
    carrier.position = Vec2(st.pitch.length - 8.0, 34.0)  # dentro del area rival
    st.ball.owner = carrier
    st.ball.position = carrier.position
    defender = st.away[1]
    engine._attempt_tackle(defender, carrier)
    assert st.last_event == "Penal"
    assert st.ball.position == st.pitch.penalty_spot(home=False)


def test_better_tackler_wins_more():
    def wins_with(tackling):
        wins = 0
        for seed in range(60):
            st = _state()
            carrier = st.home[6]
            st.ball.owner = carrier
            st.ball.position = carrier.position
            d = st.away[1]
            d.position = carrier.position + Vec2(0.5, 0.0)
            d.player.tackling = tackling
            carrier.player.dribbling = 50.0
            engine = MatchEngine(st, new_rng(seed))
            engine._resolve_tackle()
            if st.ball.owner is d:
                wins += 1
        return wins

    assert wins_with(95.0) > wins_with(20.0)


def test_tackles_happen_in_a_real_match():
    st = _state_from_kickoff()
    engine = MatchEngine(st, new_rng(1))
    seen = set()
    for _ in range(int(300.0 / (1.0 / 30.0))):  # 5 min
        engine.step()
        if st.last_event:
            seen.add(st.last_event)
    assert "Quite" in seen  # hubo recuperaciones por quite


def test_interception_is_logged_when_rival_wins_a_loose_ball():
    st = _state()
    st.last_touch = Side.HOME            # la toco por ultimo el local...
    st.ball.owner = None
    st.ball.position = Vec2(50.0, 34.0)
    st.ball.velocity = Vec2(0.0, 0.0)
    st.away[5].position = Vec2(50.0, 34.0)  # ...y un visitante la recupera
    engine = MatchEngine(st, new_rng(1))
    engine.step()
    assert any(e.kind == "intercepta" for e in st.log)


def test_tackle_is_deterministic():
    a = MatchEngine(_state_from_kickoff(), new_rng(7))
    b = MatchEngine(_state_from_kickoff(), new_rng(7))
    a.run(8.0)
    b.run(8.0)
    assert (a.state.score_home, a.state.score_away) == (
        b.state.score_home,
        b.state.score_away,
    )
    assert a.state.ball.position == b.state.ball.position


def _state_from_kickoff():
    gen = ClubGenerator(new_rng(42))
    home = gen.generate(squad_size=16, country_code="AR", tier=LeagueTier.C)
    away = gen.generate(squad_size=16, country_code="BR", tier=LeagueTier.C)
    return kickoff_state(home, away)
