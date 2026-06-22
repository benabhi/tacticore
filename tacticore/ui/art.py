"""ASCII-art para titulos (solo ASCII, estilo arcade).

Una fuente de bloque sencilla de 5 filas. Solo se definen las letras que hacen
falta; se puede ampliar a medida que se necesiten mas. `render_banner` arma una
palabra concatenando glifos.
"""

_FONT_HEIGHT = 5

# Cada glifo son 5 filas de igual ancho. Solo letras de "TACTICORE" por ahora.
_FONT: dict[str, list[str]] = {
    "A": [" ### ", "#   #", "#####", "#   #", "#   #"],
    "C": [" ####", "#    ", "#    ", "#    ", " ####"],
    "E": ["#####", "#    ", "###  ", "#    ", "#####"],
    "I": ["###", " # ", " # ", " # ", "###"],
    "O": [" ### ", "#   #", "#   #", "#   #", " ### "],
    "R": ["#### ", "#   #", "#### ", "#  # ", "#   #"],
    "T": ["#####", "  #  ", "  #  ", "  #  ", "  #  "],
    " ": ["  ", "  ", "  ", "  ", "  "],
}


def render_banner(text: str, gap: int = 1) -> list[str]:
    """Devuelve las filas (strings) de `text` dibujado en ASCII-art."""
    text = text.upper()
    rows = [""] * _FONT_HEIGHT
    separator = " " * gap
    for index, char in enumerate(text):
        glyph = _FONT.get(char, _FONT[" "])
        for r in range(_FONT_HEIGHT):
            rows[r] += glyph[r]
            if index != len(text) - 1:
                rows[r] += separator
    return rows
