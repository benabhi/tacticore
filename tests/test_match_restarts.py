"""Tests de salidas del campo y reanudaciones: lateral, corner, saque de arco (G1)."""

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


def _playing_state():
    gen = ClubGenerator(new_rng(42))
    home = gen.generate(squad_size=16, country_code="AR", tier=LeagueTier.C)
    away = gen.generate(squad_size=16, country_code="BR", tier=LeagueTier.C)
    st = kickoff_state(home, away)
    st.phase = MatchPhase.PLAYING  # evita que el primer step saque del medio
    st.ball.owner = None
    return st


def test_sideline_is_a_throw_in_for_the_other_team():
    st = _playing_state()
    st.last_touch = Side.HOME
    st.ball.position = Vec2(50.0, 0.2)
    st.ball.velocity = Vec2(0.0, -10.0)  # se va por la banda (y < 0)
    engine = MatchEngine(st, new_rng(1))
    engine.step()
    assert st.last_event == "Lateral"
    # La pelota vuelve sobre la banda, quieta, esperando el saque.
    assert 0.0 <= st.ball.position.y < 1.0
    assert st.ball.velocity.length() == 0.0
    assert st.ball.owner is None


def test_defender_last_touch_is_a_corner():
    st = _playing_state()
    st.last_touch = Side.AWAY  # AWAY defiende el arco en x = length
    st.ball.position = Vec2(st.pitch.length - 0.2, 52.0)  # fondo, fuera del arco
    st.ball.velocity = Vec2(10.0, 0.0)
    engine = MatchEngine(st, new_rng(1))
    engine.step()
    assert st.last_event == "Corner"
    # Sale por el corner del lado donde se fue (y > mitad -> esquina y=ancho).
    assert st.ball.position.x > st.pitch.length - 1.0
    assert st.ball.position.y > st.pitch.width - 1.0


def test_attacker_last_touch_is_a_goal_kick():
    st = _playing_state()
    st.last_touch = Side.HOME  # HOME ataca x = length: ultimo toque del atacante
    st.ball.position = Vec2(st.pitch.length - 0.2, 52.0)
    st.ball.velocity = Vec2(10.0, 0.0)
    engine = MatchEngine(st, new_rng(1))
    engine.step()
    assert st.last_event == "Saque de arco"
    # Sale desde el borde del area chica defendida (x ~ length - 5.5, centrado).
    assert abs(st.ball.position.x - (st.pitch.length - 5.5)) < 0.6
    assert abs(st.ball.position.y - st.pitch.width / 2) < 1.0


def test_only_restart_team_can_take_the_ball():
    st = _playing_state()
    st.last_touch = Side.HOME
    st.ball.position = Vec2(50.0, 0.2)
    st.ball.velocity = Vec2(0.0, -10.0)
    engine = MatchEngine(st, new_rng(1))
    engine.step()  # genera el lateral (saque para AWAY)
    assert engine._restart_side is Side.AWAY

    # Equipo equivocado (HOME) encima; alejamos a los AWAY para que ninguno
    # del que saca llegue. Tras la pausa, con solo HOME cerca, no se pone en juego.
    st.home[5].position = st.ball.position
    for mp in st.away:
        mp.position = Vec2(10.0, 10.0)
    engine.run(3.0)  # pasa la pausa de pelota muerta
    assert st.ball.owner is None              # el equipo equivocado no la tomo
    assert engine._restart_side is Side.AWAY  # el saque sigue pendiente

    # Cuando un jugador del que saca (AWAY) llega a la pelota, la pone en juego.
    st.away[5].position = st.ball.position
    engine.run(0.3)
    assert engine._restart_side is None       # saque ejecutado: pelota en juego


def test_restarts_keep_the_ball_inside():
    # Un partido largo nunca deja la pelota fuera del campo.
    st = kickoff_state(*_two_clubs())
    engine = MatchEngine(st, new_rng(5))
    engine.run(30.0)
    assert st.pitch.contains(st.ball.position)


def _two_clubs():
    gen = ClubGenerator(new_rng(42))
    home = gen.generate(squad_size=16, country_code="AR", tier=LeagueTier.C)
    away = gen.generate(squad_size=16, country_code="BR", tier=LeagueTier.C)
    return home, away
