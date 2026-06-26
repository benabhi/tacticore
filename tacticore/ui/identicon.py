"""Identicon ASCII de un club: un emblema unico e irrepetible por nombre.

En vez de escudos, cada club tiene un identicon: una grilla 5x5 SIMETRICA
(espejada) con dos tonos (relleno `##` y sombra `::`) y un COLOR, todo derivado
de un hash del nombre. Es determinista: el mismo nombre da siempre el mismo
emblema y color. El color es la identidad del club y se reusa en versus, listas,
etc.

Solo ASCII (directiva 2). El dos-tonos lo dan los caracteres `#`/`:`: en
truecolor la sombra ademas se oscurece; en ANSI 16 va en el mismo color (no se
depende del par brillante/normal, directiva 3). Si dos clubes caen en el mismo
color, igual se distinguen por el glifo del patron.
"""

import hashlib

from rich.text import Text

from .palette import IDENTICON_COLORS, MUTED

_SIZE = 5            # grilla 5x5
_CELL = "  "         # ancho de celda vacia (2 chars: el emblema se ve cuadrado)


def _digest(name: str) -> bytes:
    """Hash estable del nombre (insensible a mayusculas/espacios al borde)."""
    return hashlib.md5(name.strip().lower().encode("utf-8")).digest()


def identicon_color(name: str) -> str:
    """Color de identidad del club (de la paleta), derivado del nombre."""
    return IDENTICON_COLORS[_digest(name)[15] % len(IDENTICON_COLORS)]


def identicon_grid(name: str) -> list[list[int]]:
    """Grilla 5x5 de niveles (0 vacio, 1 sombra, 2 relleno), espejada izq-der."""
    h = _digest(name)
    grid: list[list[int]] = []
    i = 0
    for _ in range(_SIZE):
        left = [h[i + c] % 3 for c in range(3)]
        i += 3
        grid.append([left[0], left[1], left[2], left[1], left[0]])
    return grid


def _shade_of(color: str) -> str:
    """Tono mas oscuro para la sombra (solo truecolor; en ANSI, el mismo color)."""
    if color.startswith("#") and len(color) == 7:
        r, g, b = (int(color[k:k + 2], 16) for k in (1, 3, 5))
        return f"#{int(r * 0.5):02x}{int(g * 0.5):02x}{int(b * 0.5):02x}"
    return color


def render_identicon(name: str) -> Text:
    """Devuelve SOLO el emblema (sin nombre) como `rich.Text`, para un Static.

    El nombre del club se muestra aparte (otro Static centrado en la columna) para
    que un nombre largo no corra el emblema: asi cada uno queda centrado por su
    cuenta. Sin nombre todavia, devuelve el marco vacio (mismo tamano).
    """
    inner = _SIZE * 2
    border = "+" + "-" * inner + "+"
    t = Text()
    if not name.strip():
        t.append(border + "\n", style=MUTED)
        for _ in range(_SIZE):
            t.append("|" + " " * inner + "|\n", style=MUTED)
        t.append(border, style=MUTED)
        return t
    grid = identicon_grid(name)
    color = identicon_color(name)
    shade = _shade_of(color)
    t.append(border + "\n", style=MUTED)
    for row in grid:
        t.append("|", style=MUTED)
        for lvl in row:
            if lvl == 2:
                t.append("##", style=color)
            elif lvl == 1:
                t.append("::", style=shade)
            else:
                t.append(_CELL)
        t.append("|\n", style=MUTED)
    t.append(border, style=MUTED)
    return t
