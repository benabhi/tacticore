"""Tests del arquero: libero que sube, distribucion con variantes, color."""

from tacticore.core.rng import new_rng
from tacticore.domain.enums import LeagueTier
from tacticore.generators import ClubGenerator
from tacticore.simulation.match import MatchEngine, MatchPhase, Side, Vec2, kickoff_state
from tacticore.simulation.match import ai
from tacticore.ui.widgets.pitch import GK_COLOR, GK_OWNER_COLOR, compose_match_cells


def _state(playing=True):
    gen = ClubGenerator(new_rng(42))
    home = gen.generate(squad_size=16, country_code="AR", tier=LeagueTier.C)
    away = gen.generate(squad_size=16, country_code="BR", tier=LeagueTier.C)
    st = kickoff_state(home, away)
    if playing:
        st.phase = MatchPhase.PLAYING
    return st


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


def test_keeper_sweeps_up_when_team_attacks():
    st = _state()
    gk = ai.team_goalkeeper(st, Side.HOME)  # HOME defiende x=0
    gk.position = Vec2(5.0, 34.0)
    st.ball.position = Vec2(95.0, 34.0)  # equipo atacando: la pelota arriba
    attack = ai.goalkeeper_velocity(gk, st)
    st.ball.position = Vec2(8.0, 34.0)   # defendiendo: pelota cerca del arco
    defend = ai.goalkeeper_velocity(gk, st)
    assert attack.x > 0       # sube a hacer de libero
    assert defend.x <= 0      # se queda sobre la linea


def test_short_option_finds_open_nearby_mate():
    st = _state()
    gk = ai.team_goalkeeper(st, Side.HOME)
    mate = st.home[1]
    mate.position = gk.position + Vec2(12.0, 4.0)
    for m in st.home:
        if m not in (gk, mate):
            m.position = Vec2(60.0, 60.0)
    for o in st.away:
        o.position = Vec2(90.0, 10.0)
    assert ai.goalkeeper_short_option(gk, st) is mate


def test_keeper_plays_short_when_free():
    engine = MatchEngine(_state(), new_rng(1))
    engine._rng = _FakeRng([0.0])  # decide jugar corto
    st = engine.state
    gk = ai.team_goalkeeper(st, Side.HOME)
    gk.player.passing = gk.player.composure = 80.0
    st.ball.owner = gk
    st.ball.position = gk.position
    mate = st.home[1]
    mate.position = gk.position + Vec2(12.0, 4.0)
    for m in st.home:
        if m not in (gk, mate):
            m.position = Vec2(40.0, 60.0)
    for o in st.away:
        o.position = Vec2(90.0, 60.0)  # nadie presiona al arquero
    engine._goalkeeper_distribute(gk)
    assert st.log[-1].kind == "saque_corto"
    assert st.ball.owner is None and st.ball.velocity.length() > 0.0


def test_pressured_keeper_clears_long():
    engine = MatchEngine(_state(), new_rng(1))
    st = engine.state
    gk = ai.team_goalkeeper(st, Side.HOME)
    st.ball.owner = gk
    st.ball.position = gk.position
    st.away[1].position = gk.position + Vec2(2.0, 0.0)  # rival encima: presionado
    engine._goalkeeper_distribute(gk)
    assert st.log[-1].kind == "despeje"


def test_keepers_render_in_their_own_color():
    st = _state(playing=False)
    chars, fg, w, h = compose_match_cells(st, 78, 24)
    colors = {fg[r][c] for r in range(h) for c in range(w) if fg[r][c]}
    assert GK_COLOR in colors


def test_keeper_with_ball_renders_in_lit_color():
    st = _state(playing=False)
    gk = ai.team_goalkeeper(st, Side.HOME)
    st.ball.owner = gk
    st.ball.position = gk.position
    chars, fg, w, h = compose_match_cells(st, 78, 24)
    colors = {fg[r][c] for r in range(h) for c in range(w) if fg[r][c]}
    assert GK_OWNER_COLOR in colors  # el arquero con la pelota va en su tono claro
