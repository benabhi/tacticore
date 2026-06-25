"""Tests de los roles de formacion y la linea defensiva (H1)."""

from collections import Counter

from tacticore.core.rng import new_rng
from tacticore.domain.enums import LeagueTier
from tacticore.generators import ClubGenerator
from tacticore.simulation.match import (
    FORMATION_11,
    FORMATION_11_442,
    MatchEngine,
    MatchPhase,
    Role,
    Side,
    Vec2,
    kickoff_state,
)
from tacticore.simulation.match import ai


def _state():
    gen = ClubGenerator(new_rng(42))
    home = gen.generate(squad_size=16, country_code="AR", tier=LeagueTier.C)
    away = gen.generate(squad_size=16, country_code="BR", tier=LeagueTier.C)
    return kickoff_state(home, away)


def test_formation_4_3_3_assigns_roles():
    roles = Counter(m.role for m in _state().home)
    assert roles[Role.GOALKEEPER] == 1
    assert roles[Role.FULLBACK] == 2
    assert roles[Role.CENTER_BACK] == 2
    assert roles[Role.MIDFIELDER] == 3
    assert roles[Role.WINGER] == 2
    assert roles[Role.STRIKER] == 1


def test_wingers_start_wide():
    wings = [m for m in _state().home if m.role is Role.WINGER]
    for w in wings:  # pegados a una banda (cancha 68 de ancho)
        assert w.base_position.y < 20.0 or w.base_position.y > 48.0


def test_goalkeeper_detected_by_role():
    st = _state()
    gk = ai.team_goalkeeper(st, Side.HOME)
    assert gk is not None and gk.role is Role.GOALKEEPER


def test_defensive_line_follows_the_deepest_attacker():
    st = _state()
    before = ai.defensive_line_x(st, Side.HOME)  # HOME defiende x=0
    st.away[9].position = Vec2(25.0, 34.0)        # un rival se adelanta hacia el arco
    after = ai.defensive_line_x(st, Side.HOME)
    assert after < before  # la linea acompana: baja con el atacante


def test_kickoff_is_a_pass_between_teammates():
    st = _state()
    MatchEngine(st, new_rng(1)).run(12.0)  # pasa el delay pre-partido y saca del medio
    assert st.log and st.log[0].kind == "pase"
    assert st.log[0].player and st.log[0].target  # de un jugador a un companero


def test_teams_can_use_different_formations():
    gen = ClubGenerator(new_rng(42))
    home = gen.generate(squad_size=16, country_code="AR", tier=LeagueTier.C)
    away = gen.generate(squad_size=16, country_code="BR", tier=LeagueTier.C)
    st = kickoff_state(home, away, home_formation=FORMATION_11, away_formation=FORMATION_11_442)
    home_strikers = sum(1 for m in st.home if m.role is Role.STRIKER)
    away_strikers = sum(1 for m in st.away if m.role is Role.STRIKER)
    assert home_strikers == 1 and away_strikers == 2  # 4-3-3 vs 4-4-2


def test_winger_in_wide_advanced_zone_crosses():
    st = _state()
    st.phase = MatchPhase.PLAYING
    winger = next(m for m in st.home if m.role is Role.WINGER)
    winger.position = Vec2(st.pitch.length - 6.0, 8.0)  # BIEN al fondo y pegado a la banda
    st.ball.owner = winger
    st.ball.position = winger.position
    engine = MatchEngine(st, new_rng(1))
    engine._owner_action(winger)
    assert st.log and st.log[-1].kind == "centro"


def test_fullback_overlapping_wide_and_deep_crosses():
    st = _state()
    st.phase = MatchPhase.PLAYING
    fb = next(m for m in st.home if m.role is Role.FULLBACK)
    fb.position = Vec2(st.pitch.length - 8.0, 6.0)  # lateral que desbordo hasta el fondo
    st.ball.owner = fb
    st.ball.position = fb.position
    engine = MatchEngine(st, new_rng(1))
    engine._owner_action(fb)
    assert st.log and st.log[-1].kind == "centro"


def test_cross_opens_a_flight_window_and_box_targets():
    st = _state()
    st.phase = MatchPhase.PLAYING
    winger = next(m for m in st.home if m.role is Role.WINGER)
    winger.position = Vec2(st.pitch.length - 6.0, 6.0)
    st.ball.owner = winger
    st.ball.position = winger.position
    engine = MatchEngine(st, new_rng(1))
    engine._owner_action(winger)  # tira el centro
    assert engine._cross_flight_timer > 0.0  # se abre la ventana del centro
    # los de adentro apuntan al area rival a esperar el cabezazo
    striker = next(m for m in st.home if m.role is Role.STRIKER)
    target = ai.box_crash_target(striker, st)
    goal = ai.attacking_goal(st, Side.HOME)
    assert abs(target.x - goal.x) < 17.0  # dentro / al borde del area
