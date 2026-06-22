"""Tests del modelo geometrico de la cancha (sin UI)."""

import math

from tacticore.simulation.match import GridMap, Pitch, Rect, Vec2


# --- Vec2 ---

def test_vec2_arithmetic():
    a, b = Vec2(1.0, 2.0), Vec2(3.0, 4.0)
    assert a + b == Vec2(4.0, 6.0)
    assert b - a == Vec2(2.0, 2.0)
    assert a * 2 == Vec2(2.0, 4.0)
    assert 2 * a == Vec2(2.0, 4.0)


def test_vec2_length_and_distance():
    assert Vec2(3.0, 4.0).length() == 5.0
    assert Vec2(0.0, 0.0).distance_to(Vec2(3.0, 4.0)) == 5.0


def test_vec2_normalized_and_clamped():
    n = Vec2(0.0, 8.0).normalized()
    assert math.isclose(n.length(), 1.0)
    assert Vec2(0.0, 0.0).normalized() == Vec2(0.0, 0.0)
    # clamped no agranda si ya es mas corto:
    assert Vec2(1.0, 0.0).clamped(5.0) == Vec2(1.0, 0.0)
    # y acota si es mas largo:
    assert Vec2(10.0, 0.0).clamped(2.0) == Vec2(2.0, 0.0)


# --- Rect ---

def test_rect_contains_and_clamp():
    r = Rect(0.0, 0.0, 10.0, 4.0)
    assert r.contains(Vec2(5.0, 2.0))
    assert not r.contains(Vec2(11.0, 2.0))
    assert r.center == Vec2(5.0, 2.0)
    assert r.clamp(Vec2(20.0, -3.0)) == Vec2(10.0, 0.0)


# --- Pitch ---

def test_pitch_key_locations():
    p = Pitch()  # 105 x 68
    assert p.center == Vec2(52.5, 34.0)
    assert p.home_goal == Vec2(0.0, 34.0)
    assert p.away_goal == Vec2(105.0, 34.0)
    # El punto de penal propio cae dentro del area grande propia.
    assert p.penalty_area(home=True).contains(p.penalty_spot(home=True))


def test_pitch_clamp_keeps_inside():
    p = Pitch()
    out = Vec2(200.0, -10.0)
    clamped = p.clamp(out)
    assert p.contains(clamped)
    assert clamped == Vec2(105.0, 0.0)


# --- GridMap ---

def test_gridmap_corners_and_center():
    grid = GridMap(cols=77, rows=21, pitch=Pitch())
    assert grid.to_cell(Vec2(0.0, 0.0)) == (0, 0)
    # Esquina opuesta queda acotada a la ultima celda.
    assert grid.to_cell(Vec2(105.0, 68.0)) == (76, 20)


def test_gridmap_roundtrip_cell_center():
    grid = GridMap(cols=77, rows=21, pitch=Pitch())
    for col, row in [(0, 0), (38, 10), (76, 20)]:
        assert grid.to_cell(grid.to_meters(col, row)) == (col, row)
