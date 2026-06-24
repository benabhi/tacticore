"""Tests de los roles de formacion y la linea defensiva (H1)."""

from collections import Counter

from tacticore.core.rng import new_rng
from tacticore.domain.enums import LeagueTier
from tacticore.generators import ClubGenerator
from tacticore.simulation.match import Role, Side, Vec2, kickoff_state
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
