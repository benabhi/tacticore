"""Tests del arbitro: presencia y seguimiento de la jugada a distancia (G0)."""

from tacticore.core.rng import new_rng
from tacticore.domain.enums import LeagueTier
from tacticore.generators import ClubGenerator
from tacticore.simulation.match import MatchEngine, kickoff_state


def _fresh_state():
    gen = ClubGenerator(new_rng(42))
    home = gen.generate(squad_size=16, country_code="AR", tier=LeagueTier.C)
    away = gen.generate(squad_size=16, country_code="BR", tier=LeagueTier.C)
    return kickoff_state(home, away)


def test_referee_starts_near_center_off_the_ball():
    st = _fresh_state()
    # Arranca cerca del centro pero NO encima de la pelota/pasador del saque.
    assert st.referee.position.distance_to(st.pitch.center) > 1.0
    assert st.referee.position.distance_to(st.ball.position) > 5.0


def test_referee_follows_the_play():
    st = _fresh_state()
    start = st.referee.position
    engine = MatchEngine(st, new_rng(1))
    engine.run(8.0)
    # Se movio de su lugar inicial siguiendo la jugada...
    assert st.referee.position.distance_to(start) > 1.0
    # ...pero se mantiene a distancia razonable de la pelota (no la disputa).
    assert st.referee.position.distance_to(st.ball.position) > 1.0


def test_referee_keeps_following_distance():
    st = _fresh_state()
    engine = MatchEngine(st, new_rng(3))
    # Tras un rato de juego el arbitro queda cerca (pero no encima) de la pelota.
    far = 0
    for _ in range(300):
        engine.step()
        d = st.referee.position.distance_to(st.ball.position)
        if d > 30.0:
            far += 1
    # Casi nunca queda muy lejos: sigue la jugada.
    assert far < 30


def test_referee_is_deterministic():
    a = MatchEngine(_fresh_state(), new_rng(7))
    b = MatchEngine(_fresh_state(), new_rng(7))
    a.run(5.0)
    b.run(5.0)
    assert a.state.referee.position == b.state.referee.position
