"""Tests del widget de partido (dibujar jugadores y pelota sobre la cancha)."""

from tacticore.core.rng import new_rng
from tacticore.domain.enums import LeagueTier
from tacticore.generators import ClubGenerator
from tacticore.simulation.match import MatchEngine, kickoff_state
from tacticore.ui.widgets.pitch import (
    AWAY_COLOR,
    BALL_COLOR,
    BALL_GLYPH,
    HOME_COLOR,
    compose_match_cells,
    paint_match,
    player_glyph,
)


def _state():
    gen = ClubGenerator(new_rng(42))
    home = gen.generate(squad_size=16, country_code="AR", tier=LeagueTier.C)
    away = gen.generate(squad_size=16, country_code="BR", tier=LeagueTier.C)
    return kickoff_state(home, away)


def test_player_glyph():
    assert player_glyph(7) == "7"
    assert player_glyph(1) == "1"
    assert player_glyph(10) == "a"
    assert player_glyph(None) == "?"


def test_ball_is_drawn_on_top():
    st = _state()
    MatchEngine(st, new_rng(1)).run(2.0)  # saca la pelota del centro
    chars, fg, w, h = compose_match_cells(st, 78, 24)
    found = any(
        chars[r][c] == BALL_GLYPH and fg[r][c] == BALL_COLOR
        for r in range(h)
        for c in range(w)
    )
    assert found


def test_both_teams_appear():
    chars, fg, w, h = compose_match_cells(_state(), 78, 24)
    colors = {fg[r][c] for r in range(h) for c in range(w) if fg[r][c]}
    assert HOME_COLOR in colors
    assert AWAY_COLOR in colors


def test_paint_has_exact_dimensions():
    text = paint_match(_state(), 78, 24)
    lines = text.plain.split("\n")
    assert len(lines) == 24
    assert all(len(line) == 78 for line in lines)


def test_paint_without_state_is_just_the_field():
    # Sin estado no rompe: dibuja la cancha vacia.
    text = paint_match(None, 78, 24)
    assert text.plain.count("\n") == 23
