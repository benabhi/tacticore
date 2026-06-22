"""Tests del ASCII-art de titulos."""

from tacticore.ui.art import render_banner


def test_banner_rows_have_equal_width():
    rows = render_banner("TACTICORE")
    assert len(rows) == 5
    assert len({len(r) for r in rows}) == 1  # todas las filas igual de anchas


def test_banner_fits_in_screen():
    rows = render_banner("TACTICORE")
    assert len(rows[0]) <= 80


def test_banner_is_pure_ascii():
    for row in render_banner("TACTICORE"):
        for ch in row:
            assert 0x20 <= ord(ch) <= 0x7E
