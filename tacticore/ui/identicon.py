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


def emblem_lines(name: str) -> list[Text]:
    """Devuelve el emblema como una lista de filas `Text` (7 filas, 12 columnas).

    Util para componerlo al lado de otro contenido (el frame de una seccion es un
    solo `Static`, asi que las filas se combinan a mano). Sin nombre, devuelve el
    marco vacio del mismo tamaño.
    """
    inner = _SIZE * 2
    border = "+" + "-" * inner + "+"
    rows: list[Text] = []
    if not name.strip():
        rows.append(Text(border, style=MUTED))
        for _ in range(_SIZE):
            rows.append(Text("|" + " " * inner + "|", style=MUTED))
        rows.append(Text(border, style=MUTED))
        return rows

    grid = identicon_grid(name)
    color = identicon_color(name)
    shade = _shade_of(color)
    rows.append(Text(border, style=MUTED))
    for grid_row in grid:
        line = Text()
        line.append("|", style=MUTED)
        for lvl in grid_row:
            if lvl == 2:
                line.append("##", style=color)
            elif lvl == 1:
                line.append("::", style=shade)
            else:
                line.append(_CELL)
        line.append("|", style=MUTED)
        rows.append(line)
    rows.append(Text(border, style=MUTED))
    return rows


def render_identicon(name: str) -> Text:
    """Devuelve SOLO el emblema (sin nombre) como `rich.Text`, para un Static.

    El nombre del club se muestra aparte (otro Static centrado en la columna) para
    que un nombre largo no corra el emblema: asi cada uno queda centrado por su
    cuenta. Sin nombre todavia, devuelve el marco vacio (mismo tamano).
    """
    t = Text()
    lines = emblem_lines(name)
    for i, line in enumerate(lines):
        t.append_text(line)
        if i < len(lines) - 1:
            t.append("\n")
    return t
