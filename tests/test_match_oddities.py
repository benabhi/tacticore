"""Tests de rarezas: offside y mano (G6)."""

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
from tacticore.simulation.match import ai


def _state():
    gen = ClubGenerator(new_rng(42))
    home = gen.generate(squad_size=16, country_code="AR", tier=LeagueTier.C)
    away = gen.generate(squad_size=16, country_code="BR", tier=LeagueTier.C)
    st = kickoff_state(home, away)
    st.phase = MatchPhase.PLAYING
    return st


def test_advanced_receiver_is_offside():
    st = _state()
    owner = st.home[4]  # HOME ataca hacia +x
    mate = st.home[6]
    st.ball.position = Vec2(60.0, 34.0)
    mate.position = Vec2(101.0, 34.0)  # mas adelante que toda la defensa
    assert ai.is_offside(mate, owner, st) is True


def test_receiver_behind_the_line_is_onside():
    st = _state()
    owner = st.home[4]
    mate = st.home[6]
    st.ball.position = Vec2(60.0, 34.0)
    mate.position = Vec2(70.0, 34.0)  # adelantado pero detras del anteultimo defensor
    assert ai.is_offside(mate, owner, st) is False


def test_offside_awards_free_kick_to_defence():
    engine = MatchEngine(_state(), new_rng(1))
    st = engine.state
    owner = st.home[4]
    mate = st.home[6]
    mate.position = Vec2(101.0, 34.0)
    engine._award_offside(owner, mate)
    assert st.last_event == "Offside"
    assert st.ball.owner is None
    assert engine._restart_side is Side.AWAY  # saca la defensa


def test_handball_gives_set_piece_to_the_rival():
    engine = MatchEngine(_state(), new_rng(1))
    st = engine.state
    offender = st.home[3]
    st.ball.position = Vec2(50.0, 34.0)  # mediocampo: tiro libre, no penal
    engine._award_handball(offender)
    assert st.last_event == "Mano"
    assert engine._restart_side is Side.AWAY  # para el rival del infractor


def test_handball_in_own_box_is_a_penalty():
    engine = MatchEngine(_state(), new_rng(1))
    st = engine.state
    offender = st.home[3]  # HOME defiende el arco en x = 0
    st.ball.position = Vec2(8.0, 34.0)  # dentro del area propia
    engine._award_handball(offender)
    assert st.last_event == "Penal"
    assert st.ball.position == st.pitch.penalty_spot(home=True)
    assert engine._restart_side is Side.AWAY


def test_oddities_are_deterministic():
    a = MatchEngine(kickoff_state(*_clubs()), new_rng(7))
    b = MatchEngine(kickoff_state(*_clubs()), new_rng(7))
    a.run(8.0)
    b.run(8.0)
    assert a.state.ball.position == b.state.ball.position


def _clubs():
    gen = ClubGenerator(new_rng(42))
    home = gen.generate(squad_size=16, country_code="AR", tier=LeagueTier.C)
    away = gen.generate(squad_size=16, country_code="BR", tier=LeagueTier.C)
    return home, away
