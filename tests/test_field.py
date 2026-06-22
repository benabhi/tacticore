"""Tests del widget de cancha (logica de dibujo, sin UI)."""

from soccer_manager.ui.widgets.field import CH_KICKOFF, build_field


def test_field_dimensions_are_odd():
    # Con un area par (80x24) la cancha se fuerza a impar (79x23).
    rows = build_field(80, 24)
    assert len(rows) == 23
    assert all(len(row) == 79 for row in rows)


def test_field_has_exact_center():
    # El punto central de saque va en la interseccion fila/columna central.
    rows = build_field(80, 24)
    cy = len(rows) // 2
    cx = len(rows[0]) // 2
    assert rows[cy][cx] == CH_KICKOFF


def test_field_is_pure_ascii():
    # Directiva: todo lo que se dibuja debe ser ASCII imprimible (0x20-0x7E).
    rows = build_field(80, 24)
    for row in rows:
        for ch in row:
            assert 0x20 <= ord(ch) <= 0x7E, f"caracter no ASCII: {ch!r}"
