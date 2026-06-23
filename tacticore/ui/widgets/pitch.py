"""Widget del partido: la cancha con los jugadores y la pelota dibujados encima.

Cada jugador (metros) se mapea a una celda con `GridMap` y se pinta con su
numero (1-9, despues letras) en el color de su equipo; la pelota va siempre
encima de todo. Pensado para refrescarse en cada tick del motor (lo orquesta la
pantalla del partido).

Solo ASCII + colores ANSI (directivas 2 y 3); el cesped reusa la excepcion
temporal de [field.py](field.py).
"""

from rich.text import Text
from textual.widget import Widget

from ...simulation.match import GridMap, MatchState
from .field import (
    GRASS_DARK,
    GRASS_LIGHT,
    LINE_COLOR,
    STRIPE_WIDTH,
    build_field,
)

# Colores de cada equipo y de la pelota (ANSI estandar).
HOME_COLOR = "bright_cyan"
AWAY_COLOR = "bright_red"
BALL_COLOR = "bright_yellow"
BALL_GLYPH = "o"  # redonda y centrada en la celda (lo mas parecido a un '.' centrado en ASCII)


def player_glyph(number: int | None) -> str:
    """Un solo caracter para el dorsal: 1-9, luego a-z, y '#' si se pasa."""
    if number is None:
        return "?"
    if 1 <= number <= 9:
        return str(number)
    idx = number - 10
    if 0 <= idx < 26:
        return chr(ord("a") + idx)
    return "#"


def compose_match_cells(
    state: MatchState | None, width: int, height: int
) -> tuple[list[list[str]], list[list[str | None]], int, int]:
    """Arma las grillas de caracteres y de color sobre las que se pinta.

    Devuelve `(chars, fg, eff_w, eff_h)`: la cancha (con jugadores y pelota ya
    superpuestos), el color de frente por celda (None = sin override) y el
    tamano efectivo (impar) que `build_field` termino usando.
    """
    rows = build_field(width, height)
    eff_h = len(rows)
    eff_w = len(rows[0]) if rows else 0
    chars = [list(r) for r in rows]
    fg: list[list[str | None]] = [[None] * eff_w for _ in range(eff_h)]

    if state is not None and eff_w and eff_h:
        grid = GridMap(cols=eff_w, rows=eff_h, pitch=state.pitch)

        def place(mp, color: str) -> None:
            col, row = grid.to_cell(mp.position)
            chars[row][col] = player_glyph(mp.number)
            fg[row][col] = color

        for mp in state.home:
            place(mp, HOME_COLOR)
        for mp in state.away:
            place(mp, AWAY_COLOR)
        # La pelota se dibuja al final: siempre queda encima.
        bc, br = grid.to_cell(state.ball.position)
        chars[br][bc] = BALL_GLYPH
        fg[br][bc] = BALL_COLOR

    return chars, fg, eff_w, eff_h


def paint_match(state: MatchState | None, width: int, height: int) -> Text:
    """Pinta la cancha con jugadores/pelota como un `Text` de `width` x `height`."""
    chars, fg, eff_w, eff_h = compose_match_cells(state, width, height)
    text = Text(no_wrap=True)
    cx = eff_w // 2
    for r in range(height):
        for c in range(width):
            in_grid = r < eff_h and c < eff_w
            ch = chars[r][c] if in_grid else " "
            f = fg[r][c] if in_grid else None
            # Franja de cesped segun la distancia a la columna central.
            band = (abs(c - cx) + STRIPE_WIDTH // 2) // STRIPE_WIDTH
            grass = GRASS_LIGHT if band % 2 == 0 else GRASS_DARK
            if f is not None:
                style = f"bold {f} on {grass}"
            elif ch != " ":
                style = f"{LINE_COLOR} on {grass}"
            else:
                style = f"on {grass}"
            text.append(ch, style=style)
        if r != height - 1:
            text.append("\n")
    return text


class MatchPitch(Widget):
    """Dibuja un `MatchState` (cancha + jugadores + pelota) en el area asignada.

    La pantalla setea `.state` y llama `refresh()` en cada tick del motor.
    """

    def __init__(self, state: MatchState | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.state = state

    def render(self) -> Text:
        return paint_match(self.state, self.size.width, self.size.height)
