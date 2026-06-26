"""Seleccion de pais a pantalla completa, en columnas y SIN scroll (directiva 1).

Muestra los paises del juego en 3 columnas que entran enteras en 80x25; se mueve
con las flechas y se elige con Enter (Esc cancela). Devuelve (nombre, codigo) a
la pantalla que lo abrio (via dismiss), o None si se cancela.

Recibe la lista de paises disponibles (nombre, codigo); por defecto, todos. El
juego le pasa solo los paises que existen en el mundo generado, asi el club del
jugador siempre cae en un pais con sus ligas. La cantidad de filas se adapta a
cuantos paises haya (siempre en 3 columnas, siempre dentro de 80x25).
"""

from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Static

from ...generators.data.country_data import COUNTRIES
from .base_screen import BaseScreen

_COLS = 3
_COL_W = 25  # ancho de cada columna


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

    def __init__(self, countries: list[tuple[str, str]] | None = None) -> None:
        super().__init__()
        self._countries = countries or list(COUNTRIES)
        # Filas por columna (layout column-major): se adapta a la cantidad de
        # paises manteniendo las 3 columnas. Con 6 paises son 2 filas; con 58, 20.
        self._rows = (len(self._countries) + _COLS - 1) // _COLS
        self._sel = 0

    def compose_viewport(self) -> ComposeResult:
        yield Static("ELEGI LA NACIONALIDAD DE TU CLUB", id="title")
        yield Static(self._grid_text(), id="grid")
        yield Static("Flechas: mover   Enter: elegir   Esc: cancelar", id="footer")

    def _grid_text(self) -> Text:
        t = Text()
        for r in range(self._rows):
            for c in range(_COLS):
                idx = c * self._rows + r
                if idx >= len(self._countries):
                    continue
                name = self._countries[idx][0]
                if idx == self._sel:
                    t.append(f"> {name} <".ljust(_COL_W), style="bold black on green")
                else:
                    t.append(f"  {name}".ljust(_COL_W), style="white")
            t.append("\n")
        return t

    def _refresh_grid(self) -> None:
        self.query_one("#grid", Static).update(self._grid_text())

    def action_move(self, delta: int) -> None:
        self._sel = max(0, min(len(self._countries) - 1, self._sel + delta))
        self._refresh_grid()

    def action_move_col(self, delta: int) -> None:
        self._sel = max(
            0, min(len(self._countries) - 1, self._sel + delta * self._rows)
        )
        self._refresh_grid()

    def action_choose(self) -> None:
        self.dismiss(self._countries[self._sel])

    def action_cancel(self) -> None:
        self.dismiss(None)
