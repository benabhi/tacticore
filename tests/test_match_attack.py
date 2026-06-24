"""Tests de la decision de ataque: alcance de remate, pase de gol, arquero batible."""

from tacticore.core.rng import new_rng
from tacticore.domain.enums import LeagueTier, Position
from tacticore.generators import ClubGenerator
from tacticore.simulation.match import (
    MatchEngine,
    MatchPhase,
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


def test_shoot_range_grows_with_shooting():
    base = _state().home[9].player
    import copy

    poor = copy.copy(base)
    poor.shooting = 20.0
    elite = copy.copy(base)
    elite.shooting = 95.0
    assert ai.shoot_range(elite) > ai.shoot_range(poor)


def test_better_finisher_picks_open_closer_mate():
    st = _state()
    owner = st.home[8]
    owner.position = Vec2(70.0, 34.0)  # HOME ataca x=105: a 35m del arco
    mate = st.home[9]
    mate.position = Vec2(95.0, 40.0)   # mas cerca del arco y en posicion de remate
    # Aislamos: el resto de companeros lejos.
    for m in st.home:
        if m not in (owner, mate):
            m.position = Vec2(0.0, 0.0)
    # Rivales atras (linea de offside en x=100): el companero en 95 queda HABILITADO.
    for o in st.away:
        o.position = Vec2(100.0, 64.0)
    assert ai.better_finisher(owner, st, 60.0) is mate


def test_weaker_keeper_is_beaten_more_often():
    engine = MatchEngine(_state(), new_rng(1))
    gk = next(mp for mp in engine.state.home if ai.is_goalkeeper(mp))
    gk.player.reflexes = gk.player.handling = 90.0
    strong = engine._gk_beaten_chance(gk)
    gk.player.reflexes = gk.player.handling = 20.0
    weak = engine._gk_beaten_chance(gk)
    assert weak > strong
    assert 0.0 < strong < weak <= 0.28


def test_players_shoot_during_a_match():
    gen = ClubGenerator(new_rng(42))
    home = gen.generate(squad_size=16, country_code="AR", tier=LeagueTier.C)
    away = gen.generate(squad_size=16, country_code="BR", tier=LeagueTier.C)
    st = kickoff_state(home, away)
    MatchEngine(st, new_rng(4)).run(300.0)
    remates = [e for e in st.log if e.kind == "remate"]
    assert len(remates) >= 3  # hay remates en un partido (no solo pases)
