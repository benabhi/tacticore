"""Seleccion de pais a pantalla completa, en columnas y SIN scroll (directiva 1).

Muestra los paises del juego en 3 columnas que entran enteras en 80x25; se mueve
con las flechas y se elige con Enter (Esc cancela). Devuelve (nombre, codigo) a
la pantalla que lo abrio (via dismiss), o None si se cancela.
"""

from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Static

from ...generators.data.country_data import COUNTRIES
from .base_screen import BaseScreen

_COLS = 3
_ROWS = (len(COUNTRIES) + _COLS - 1) // _COLS  # filas por columna
_COL_W = 25                                    # ancho de cada columna


class CountrySelectScreen(BaseScreen):
    """Grilla de paises en columnas; elige con las flechas + Enter."""

    BINDINGS = [
        ("up", "move(-1)", "Arriba"),
        ("down", "move(1)", "Abajo"),
        ("left", "move_col(-1)", "Izquierda"),
        ("right", "move_col(1)", "Derecha"),
        ("enter", "choose", "Elegir"),
        ("escape", "cancel", "Cancelar"),
    ]

    CSS = """
    #viewport {
        align: center top;
    }
    #title {
        width: 1fr;
        text-align: center;
        color: green;
        text-style: bold;
        padding: 1 0;
    }
    #grid {
        width: 78;
        height: auto;
    }
    #footer {
        width: 1fr;
        text-align: center;
        color: $text-muted;
        padding: 1 0 0 0;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._sel = 0

    def compose_viewport(self) -> ComposeResult:
        yield Static("ELEGI LA NACIONALIDAD DE TU CLUB", id="title")
        yield Static(self._grid_text(), id="grid")
        yield Static("Flechas: mover   Enter: elegir   Esc: cancelar", id="footer")

    def _grid_text(self) -> Text:
        t = Text()
        for r in range(_ROWS):
            for c in range(_COLS):
                idx = c * _ROWS + r
                if idx >= len(COUNTRIES):
                    continue
                name = COUNTRIES[idx][0]
                if idx == self._sel:
                    t.append(f"> {name} <".ljust(_COL_W), style="bold black on green")
                else:
                    t.append(f"  {name}".ljust(_COL_W), style="white")
            t.append("\n")
        return t

    def _refresh_grid(self) -> None:
        self.query_one("#grid", Static).update(self._grid_text())

    def action_move(self, delta: int) -> None:
        self._sel = max(0, min(len(COUNTRIES) - 1, self._sel + delta))
        self._refresh_grid()

    def action_move_col(self, delta: int) -> None:
        self._sel = max(0, min(len(COUNTRIES) - 1, self._sel + delta * _ROWS))
        self._refresh_grid()

    def action_choose(self) -> None:
        self.dismiss(COUNTRIES[self._sel])

    def action_cancel(self) -> None:
        self.dismiss(None)
