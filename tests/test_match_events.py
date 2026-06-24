"""Tests del log de eventos y el relato (commentary basico)."""

from tacticore.core.rng import new_rng
from tacticore.domain.enums import LeagueTier
from tacticore.generators import ClubGenerator
from tacticore.simulation.match import MatchEngine, MatchEvent, kickoff_state
from tacticore.simulation.match.narration import MAX_WIDTH, narrate, narrate_segments


def _clubs():
    gen = ClubGenerator(new_rng(42))
    home = gen.generate(squad_size=16, country_code="AR", tier=LeagueTier.C)
    away = gen.generate(squad_size=16, country_code="BR", tier=LeagueTier.C)
    return home, away


def test_log_records_events_with_protagonist():
    st = kickoff_state(*_clubs())
    MatchEngine(st, new_rng(1)).run(150.0)
    assert st.log, "deberia haber eventos registrados"
    remates = [e for e in st.log if e.kind == "remate"]
    assert remates and remates[0].player  # el remate nombra al protagonista


def test_narration_is_a_short_ascii_line():
    st = kickoff_state(*_clubs())
    MatchEngine(st, new_rng(1)).run(60.0)
    for event in st.log:
        line = narrate(event)
        assert 0 < len(line) <= MAX_WIDTH
        assert line.isascii()


def test_narration_caps_very_long_names():
    ev = MatchEvent(tick=0, clock=0.0, kind="remate", player="X" * 200)
    assert len(narrate(ev)) <= MAX_WIDTH


def test_pass_events_are_logged_with_target_and_detail():
    st = kickoff_state(*_clubs())
    MatchEngine(st, new_rng(1)).run(60.0)
    pases = [e for e in st.log if e.kind == "pase"]
    assert pases, "deberia haber pases registrados"
    p = pases[0]
    assert p.player and p.target
    assert p.detail in ("corto", "largo")


def test_pass_narration_marks_both_player_names():
    ev = MatchEvent(
        tick=0, clock=65.0, kind="pase", player="Juan", target="Pedro", detail="corto"
    )
    segments = narrate_segments(ev)
    names = [text for text, is_name in segments if is_name]
    assert "Juan" in names and "Pedro" in names
    assert "corto" in narrate(ev)


def test_log_is_deterministic():
    a = kickoff_state(*_clubs())
    MatchEngine(a, new_rng(7)).run(30.0)
    b = kickoff_state(*_clubs())
    MatchEngine(b, new_rng(7)).run(30.0)
    assert [(e.kind, e.player) for e in a.log] == [(e.kind, e.player) for e in b.log]
