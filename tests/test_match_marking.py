"""Tests de marca / defensa: zonal con enganche, guiada por atributos (G2)."""

from tacticore.core.rng import new_rng
from tacticore.domain.enums import LeagueTier
from tacticore.generators import ClubGenerator
from tacticore.simulation.match import (
    DEFAULT_DT,
    MatchEngine,
    MatchPhase,
    Side,
    Vec2,
    kickoff_state,
)
from tacticore.simulation.match import ai


def _fresh_state():
    gen = ClubGenerator(new_rng(42))
    home = gen.generate(squad_size=16, country_code="AR", tier=LeagueTier.C)
    away = gen.generate(squad_size=16, country_code="BR", tier=LeagueTier.C)
    return kickoff_state(home, away)


def test_defender_picks_up_rival_in_its_zone():
    st = _fresh_state()
    defender = st.home[1]
    rival = st.away[1]
    rival.position = defender.base_position + Vec2(2.0, 0.0)  # dentro de la zona
    assert ai.marking_assignment(defender, st) is rival


def test_marking_point_is_goal_side():
    st = _fresh_state()
    defender = st.home[1]  # HOME defiende el arco en x = 0
    rival = st.away[1]
    rival.position = defender.base_position + Vec2(2.0, 0.0)
    point = ai.marking_point(defender, rival, st)
    # Se para entre el rival y el arco propio: mas cerca de x = 0 que el rival.
    assert point.x < rival.position.x


def test_better_reading_marks_tighter():
    st = _fresh_state()
    defender = st.home[1]
    rival = st.away[1]
    rival.position = defender.base_position + Vec2(2.0, 0.0)
    defender.player.positioning = defender.player.anticipation = 90.0
    tight = ai.marking_point(defender, rival, st).distance_to(rival.position)
    defender.player.positioning = defender.player.anticipation = 10.0
    loose = ai.marking_point(defender, rival, st).distance_to(rival.position)
    assert tight < loose


def test_work_rate_widens_the_zone():
    st = _fresh_state()
    defender = st.home[1]
    # Aislamos: todos los rivales lejos, salvo el que probamos.
    for o in st.away:
        o.position = Vec2(100.0, 60.0)
    rival = st.away[1]
    rival.position = defender.base_position + Vec2(15.0, 0.0)  # lejos del ancla
    defender.player.work_rate = 95.0
    assert ai.marking_assignment(defender, st) is rival  # llega a cubrirlo
    defender.player.work_rate = 10.0
    assert ai.marking_assignment(defender, st) is None    # no sale tan lejos


def test_marker_moves_to_track_its_rival():
    st = _fresh_state()
    st.phase = MatchPhase.PLAYING
    carrier = st.away[4]
    st.ball.owner = carrier
    st.ball.position = carrier.position
    defender = st.home[1]
    base = defender.base_position
    # Un rival fijado dentro de la zona del defensor (base, para que no vuelva).
    intruder = st.away[5]
    intruder.position = base + Vec2(6.0, 0.0)
    intruder.base_position = base + Vec2(6.0, 0.0)
    engine = MatchEngine(st, new_rng(1))
    # La marca es transitoria (solo mientras el rival tiene la pelota): medimos
    # el pico de desplazamiento, no la posicion final.
    max_moved = 0.0
    for _ in range(int(2.0 / DEFAULT_DT)):
        engine.step()
        max_moved = max(max_moved, defender.position.distance_to(base))
    assert max_moved > 1.0  # salio a marcar


def test_marking_is_deterministic():
    a = MatchEngine(_fresh_state(), new_rng(7))
    b = MatchEngine(_fresh_state(), new_rng(7))
    a.run(5.0)
    b.run(5.0)
    pa = [(mp.position.x, mp.position.y) for mp in a.state.all_players()]
    pb = [(mp.position.x, mp.position.y) for mp in b.state.all_players()]
    assert pa == pb
