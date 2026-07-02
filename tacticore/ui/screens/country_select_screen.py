"""Seleccion de pais a pantalla completa, en columnas y SIN scroll (directiva 1).

Muestra los paises en 3 columnas que entran enteras en 80x25; se mueve con las
flechas y se elige con Enter (Esc cancela). Con `/` se activa un filtro en vivo:
se escribe y la grilla se achica a los que coinciden. Devuelve (nombre, codigo) a
la pantalla que lo abrio (via dismiss), o None si se cancela.

Recibe la lista de paises disponibles (nombre, codigo) y el titulo. Se reutiliza
en "Crea tu club" (elegir nacionalidad) y en la vista de Liga (cambiar de pais).
"""

from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Static

from ...generators.data.country_data import COUNTRIES
from ..format import hint
from .base_screen import BaseScreen

_COLS = 3
_COL_W = 25  # ancho de cada columna


class CountrySelectScreen(BaseScreen):
    """Grilla de paises en columnas; flechas + Enter, con filtro en vivo (`/`)."""

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

    def __init__(
        self,
        countries: list[tuple[str, str]] | None = None,
        title: str = "ELEGI UN PAIS",
    ) -> None:
        super().__init__()
        # Orden alfabetico por nombre para que sea facil encontrar el pais.
        self._countries = sorted(countries or COUNTRIES, key=lambda c: c[0])
        self._title = title
        self._sel = 0
        self._searching = False  # filtro en vivo activo
        self._query = ""         # texto del filtro

    # --- Datos: lista visible (filtrada) ---
    def _visible(self) -> list[tuple[str, str]]:
        if not self._query:
            return self._countries
        q = self._query.lower()
        return [c for c in self._countries if q in c[0].lower()]

    @property
    def _rows(self) -> int:
        # Filas por columna (layout column-major), segun cuantos paises se ven.
        return max(1, (len(self._visible()) + _COLS - 1) // _COLS)

    def compose_viewport(self) -> ComposeResult:
        yield Static(self._title_text(), id="title")
        yield Static(self._grid_text(), id="grid")
        yield Static(self._footer_text(), id="footer")

    def _title_text(self) -> Text:
        # El prompt de busqueda va aca arriba (junto al titulo) para que siempre se
        # vea: la grilla puede ser alta y empujar el pie fuera de vista.
        t = Text(justify="center")
        t.append(self._title, style="bold green")
        if self._searching:
            t.append("      Buscar: ", style="bold yellow")
            t.append(self._query + "_", style="bold white")
        return t

    def _footer_text(self) -> Text:
        if self._searching:
            return hint(("Enter", "elegir"), ("Esc", "salir del filtro"))
        return hint(("Flechas", "mover"), ("Enter", "elegir"),
                    ("/", "buscar"), ("Esc", "cancelar"))

    def _grid_text(self) -> Text:
        visible = self._visible()
        rows = self._rows
        t = Text()
        if not visible:
            t.append(f"  Sin resultados para \"{self._query}\".", style="grey62")
            return t
        for r in range(rows):
            for c in range(_COLS):
                idx = c * rows + r
                if idx >= len(visible):
                    continue
                name = visible[idx][0]
                if idx == self._sel:
                    t.append(f"> {name} <".ljust(_COL_W), style="bold black on green")
                else:
                    t.append(f"  {name}".ljust(_COL_W), style="white")
            t.append("\n")
        return t

    def _refresh(self) -> None:
        self.query_one("#title", Static).update(self._title_text())
        self.query_one("#grid", Static).update(self._grid_text())
        self.query_one("#footer", Static).update(self._footer_text())

    def _clamp(self) -> None:
        self._sel = max(0, min(len(self._visible()) - 1, self._sel))

    # --- Navegacion (BINDINGS, solo fuera del filtro) ---
    def action_move(self, delta: int) -> None:
        self._sel = max(0, min(len(self._visible()) - 1, self._sel + delta))
        self._refresh()

    def action_move_col(self, delta: int) -> None:
        self._sel = max(
            0, min(len(self._visible()) - 1, self._sel + delta * self._rows)
        )
        self._refresh()

    def action_choose(self) -> None:
        visible = self._visible()
        if visible:
            self.dismiss(visible[self._sel])

    def action_cancel(self) -> None:
        self.dismiss(None)

    # --- Filtro en vivo con "/" ---
    def on_key(self, event) -> None:
        if self._searching:
            self._on_key_search(event)
            return
        if event.character == "/":
            event.stop()
            self._searching = True
            self._query = ""
            self._sel = 0
            self._refresh()
        # El resto (flechas/enter/escape) lo manejan los BINDINGS.

    def _on_key_search(self, event) -> None:
        key = event.key
        if key == "escape":
            event.stop()
            self._searching = False
            self._query = ""
            self._sel = 0
            self._refresh()
        elif key == "enter":
            event.stop()
            self.action_choose()
        elif key == "backspace":
            event.stop()
            self._query = self._query[:-1]
            self._sel = 0
            self._refresh()
        elif key in ("up", "down"):
            event.stop()
            self.action_move(-1 if key == "up" else 1)
        elif key in ("left", "right"):
            event.stop()
            self.action_move_col(-1 if key == "left" else 1)
        elif event.character and event.character.isprintable() and len(event.character) == 1:
            event.stop()
            self._query += event.character
            self._sel = 0
            self._refresh()
