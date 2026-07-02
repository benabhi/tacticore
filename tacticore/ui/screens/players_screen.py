"""Seccion Jugadores: la plantilla, la cantera y el mercado.

Pestañas:
- Plantilla: la tabla del plantel (interactiva: se navega y se abre la ficha).
- Cantera: juveniles (placeholder; los alimentaran los cazatalentos).
- Mercado: transferencias in/out (placeholder).

La Plantilla es la unica pestaña interactiva: recibe el teclado en `on_content_key`
(flechas para moverse, Enter para la ficha, "/" para buscar en vivo). Las demas
teclas del marco (numeros/Tab para pestañas, letras para secciones) las maneja
`SectionScreen`.
"""

from rich.text import Text

from ..format import append_section, hint
from ..player_labels import FOOT_SHORT, SPECIALTY_SHORT
from .section_screen import SectionScreen

_WIDTH = 80       # ancho total de la tabla (toda la pantalla)
_PAGE_SIZE = 14   # filas de jugadores por pagina

# Columnas: (titulo, ancho, alineacion). El nombre se calcula para llenar los 80.
_NAME_W = _WIDTH - 2 - 11 - 32
_COLUMNS = [
    ("#", 2, "r"), ("NOMBRE", _NAME_W, "l"), ("POS", 3, "l"), ("NAC", 3, "l"),
    ("ED", 2, "r"), ("PIE", 3, "l"), ("OVR", 3, "r"), ("POT", 3, "r"),
    ("FOR", 3, "r"), ("FIT", 3, "r"), ("MOR", 3, "r"), ("ESP", 4, "l"),
]
_MOR_IDX = 10
_ESP_IDX = 11

# Color de la moral (1 peor -> 5 mejor): de rojo a verde, sin leyenda aparte.
_MORALE_STYLE = {1: "bold red", 2: "red", 3: "yellow", 4: "green", 5: "bold green"}


class PlayersScreen(SectionScreen):
    """Plantilla del club (interactiva) + cantera y mercado (placeholder)."""

    section_key = "J"
    section_title = "Jugadores"
    tabs = ("Plantilla", "Cantera", "Mercado")

    def __init__(self) -> None:
        super().__init__()
        self._selected = 0    # indice del jugador seleccionado (sobre los visibles)
        self._searching = False  # si esta activo el buscador (se escribe)
        self._query = ""      # texto del filtro en vivo

    # --- Datos ---
    @property
    def _players(self) -> list:
        game = self.app.game
        if game is None or game.player_club is None:
            return []
        return game.player_club.players

    @property
    def _today(self):
        return self.app.game.calendar.current_date

    def _haystack(self, p) -> str:
        """Todos los valores visibles del jugador, en minusculas, para buscar."""
        return " ".join(self._cell_values(p)).lower()

    def _visible(self) -> list:
        """Jugadores que pasan el filtro de busqueda (todos si no hay filtro)."""
        players = self._players
        if not self._query:
            return players
        q = self._query.lower()
        return [p for p in players if q in self._haystack(p)]

    # --- Render por pestaña ---
    def render_tab(self, index: int) -> Text:
        if index == 1:
            return self._youth_text()
        if index == 2:
            return self._market_text()
        return self._table_text()

    def _youth_text(self) -> Text:
        t = Text()
        append_section(t, "CANTERA", [
            ("Todavia no hay juveniles.", "grey62"),
            "",
            ("La red de cazatalentos (en Club > Empleados) va a descubrir", "grey62"),
            ("promesas que apareceran aca para sumarlas al primer equipo.", "grey62"),
        ])
        return t

    def _market_text(self) -> Text:
        t = Text()
        append_section(t, "MERCADO", [
            ("El mercado de pases vivira aca.", "grey62"),
            "",
            ("  - Comprar y vender jugadores", "grey70"),
            ("  - Ofertas recibidas y enviadas", "grey70"),
            ("  - Jugadores en la mira", "grey70"),
            "",
            ("El valor de cada jugador ya se calcula (lo ves en su ficha).", "grey62"),
        ])
        return t

    # --- Tabla de la plantilla ---
    def _table_text(self) -> Text:
        club = self.app.game.player_club if self.app.game else None
        if not self._players:
            return Text("No hay jugadores para mostrar.", style="white")

        visible = self._visible()
        total = len(visible)
        pages = max(1, (total + _PAGE_SIZE - 1) // _PAGE_SIZE)
        self._selected = max(0, min(total - 1, self._selected)) if total else 0
        page = self._selected // _PAGE_SIZE if total else 0
        start = page * _PAGE_SIZE
        page_players = visible[start:start + _PAGE_SIZE]

        t = Text()
        subtitle = f"{club.name}   {len(self._players)} jugadores"
        if self._query:
            subtitle += f"   [{total} coinciden]"
        t.append(subtitle + "\n", style="grey62")
        self._append_header(t)
        if total == 0:
            t.append(f"  Sin resultados para \"{self._query}\".\n", style="grey62")
            shown = 1
        else:
            for offset, player in enumerate(page_players):
                self._append_row(t, player, start + offset == self._selected)
            shown = len(page_players)
        for _ in range(_PAGE_SIZE - shown):
            t.append("\n")
        t.append("\n")  # una linea de aire entre la tabla y la ayuda de teclas
        self._append_footer(t, page + 1, pages)
        return t

    def _append_footer(self, t: Text, page: int, pages: int) -> None:
        if self._searching:
            t.append("Buscar: ", style="bold yellow")
            t.append(self._query + "_", style="bold white")
            t.append("   ")
            t.append_text(hint(("Enter", "ficha"), ("Esc", "cancelar")))
        else:
            t.append_text(hint(
                ("Flechas", "mover"), ("Enter", "ficha"),
                ("/", "buscar"), ("<- ->", "pagina"),
            ))
        t.append(f"   Pag {page}/{pages}", style="grey62")

    @staticmethod
    def _fmt(text, width: int, align: str) -> str:
        text = str(text)[:width]
        return text.rjust(width) if align == "r" else text.ljust(width)

    def _append_header(self, t: Text) -> None:
        cells = [self._fmt(h, w, a) for h, w, a in _COLUMNS]
        line = ("  " + " ".join(cells)).ljust(_WIDTH)
        t.append(line + "\n", style="bold green")
        t.append("-" * _WIDTH + "\n", style="grey50")

    def _append_row(self, t: Text, p, selected: bool) -> None:
        values = self._cell_values(p)
        cells = [self._fmt(v, w, a) for v, (_, w, a) in zip(values, _COLUMNS)]
        if selected:
            line = ("> " + " ".join(cells)).ljust(_WIDTH)
            t.append(line + "\n", style="bold black on green")
            return
        t.append("  ")
        for i, cell in enumerate(cells):
            if i == _MOR_IDX:
                style = _MORALE_STYLE.get(int(cell), "white")
            elif i == _ESP_IDX:
                style = "grey42" if cell.strip() == "-" else "bold cyan"
            else:
                style = "white"
            t.append(cell, style=style)
            if i < len(cells) - 1:
                t.append(" ")
        used = 2 + sum(len(c) for c in cells) + (len(cells) - 1)
        if used < _WIDTH:
            t.append(" " * (_WIDTH - used))
        t.append("\n")

    def _cell_values(self, p) -> list:
        esp = SPECIALTY_SHORT[p.specialty] if p.specialty else "-"
        return [
            str(p.shirt_number or "-"),
            p.full_name,
            p.position.value,
            p.nationality,
            str(p.age_on(self._today)),
            FOOT_SHORT[p.foot],
            str(round(p.overall)),
            str(round(p.potential)),
            str(round(p.form)),
            str(round(p.fitness)),
            str(p.morale.value),
            esp,
        ]

    # --- Interaccion (solo en la pestaña Plantilla) ---
    def _open_detail(self) -> None:
        visible = self._visible()
        if not visible:
            return
        from .player_detail_screen import PlayerDetailScreen

        self.app.push_screen(
            PlayerDetailScreen(visible, self._selected, self._today, self._on_detail_close)
        )

    def _on_detail_close(self, index: int) -> None:
        self._selected = index
        self._refresh_content()

    def _move(self, delta: int) -> None:
        total = len(self._visible())
        if total:
            self._selected = max(0, min(total - 1, self._selected + delta))
        self._refresh_content()

    def content_captures_keys(self) -> bool:
        # Con el buscador abierto, la Plantilla consume TODO el teclado (para
        # escribir el filtro sin que el marco cambie de seccion/pestaña).
        return self._active_tab == 0 and self._searching

    def on_content_key(self, event) -> None:
        if self._active_tab != 0 or not self._players:
            return
        if self._searching:
            self._on_key_search(event, event.key)
            return
        key = event.key
        if key == "up":
            event.stop(); self._move(-1)
        elif key == "down":
            event.stop(); self._move(1)
        elif key in ("left", "pageup"):
            event.stop(); self._move(-_PAGE_SIZE)
        elif key in ("right", "pagedown"):
            event.stop(); self._move(_PAGE_SIZE)
        elif key == "enter":
            event.stop(); self._open_detail()
        elif event.character == "/":
            self._searching = True
            self._query = ""
            self._selected = 0
            event.stop(); self._refresh_content()

    def _on_key_search(self, event, key: str) -> None:
        if key == "escape":
            self._searching = False
            self._query = ""
            self._selected = 0
            event.stop(); self._refresh_content()
        elif key == "enter":
            event.stop(); self._open_detail()
        elif key == "backspace":
            self._query = self._query[:-1]
            self._selected = 0
            event.stop(); self._refresh_content()
        elif key in ("up", "down", "left", "right", "pageup", "pagedown"):
            step = {"up": -1, "down": 1, "left": -_PAGE_SIZE, "right": _PAGE_SIZE,
                    "pageup": -_PAGE_SIZE, "pagedown": _PAGE_SIZE}[key]
            event.stop(); self._move(step)
        elif event.character and event.character.isprintable() and len(event.character) == 1:
            self._query += event.character
            self._selected = 0
            event.stop(); self._refresh_content()
