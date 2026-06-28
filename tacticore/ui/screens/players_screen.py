"""Seccion Jugadores: la plantilla del club en una tabla paginada.

Muestra una fila por jugador con los datos esenciales (no todos: no entran). Se
navega con las flechas (arriba/abajo entre filas, izquierda/derecha entre
paginas) y con Enter se abre la ficha completa del jugador. Usa los 80 de ancho.
"""

from collections.abc import Iterator

from rich.text import Text
from textual.widget import Widget
from textual.widgets import Static

from ..player_labels import FOOT_SHORT, POSITION_SHORT, SPECIALTY_SHORT
from .section_screen import SectionScreen

_WIDTH = 80       # ancho total de la tabla (toda la pantalla)
_PAGE_SIZE = 14   # filas de jugadores por pagina

# Columnas: (titulo, ancho, alineacion). El nombre se calcula para llenar los 80.
# Fijas (sin el nombre) suman 32; con marcador (2) y 11 separadores -> nombre = 35.
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
    """Plantilla del club: tabla paginada y navegable, a ancho completo."""

    section_key = "J"

    CSS = """
    #content {
        padding: 1 0;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._selected = 0  # indice global del jugador seleccionado

    def content(self) -> Iterator[Widget]:
        yield Static(self._table_text(), id="roster")

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

    # --- Render de la tabla ---
    def _table_text(self) -> Text:
        players = self._players
        game = self.app.game
        club = game.player_club if game else None
        if not players:
            return Text("No hay jugadores para mostrar.", style="white")

        total = len(players)
        pages = (total + _PAGE_SIZE - 1) // _PAGE_SIZE
        self._selected = max(0, min(total - 1, self._selected))
        page = self._selected // _PAGE_SIZE
        start = page * _PAGE_SIZE
        page_players = players[start:start + _PAGE_SIZE]

        t = Text()
        t.append(f"PLANTILLA  {club.name}   ({total} jugadores)\n\n", style="bold green")
        self._append_header(t)
        for offset, player in enumerate(page_players):
            self._append_row(t, player, start + offset == self._selected)
        # Relleno para que el pie quede en su lugar aunque la pagina este corta.
        for _ in range(_PAGE_SIZE - len(page_players)):
            t.append("\n")
        t.append("\n")
        t.append("Flechas: mover   Enter: ficha   <- ->: pagina", style="grey62")
        t.append(f"        Pagina {page + 1}/{pages}\n", style="grey62")
        return t

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
            # Fila resaltada: barra verde de ancho completo.
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
            POSITION_SHORT[p.position],
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

    def _refresh(self) -> None:
        self.query_one("#roster", Static).update(self._table_text())

    # --- Teclado: navegar y abrir ficha ---
    def on_key(self, event) -> None:
        players = self._players
        if not players:
            return
        key = event.key
        total = len(players)
        if key == "up":
            self._selected = max(0, self._selected - 1)
            event.stop()
            self._refresh()
        elif key == "down":
            self._selected = min(total - 1, self._selected + 1)
            event.stop()
            self._refresh()
        elif key in ("left", "pageup"):
            self._selected = max(0, self._selected - _PAGE_SIZE)
            event.stop()
            self._refresh()
        elif key in ("right", "pagedown"):
            self._selected = min(total - 1, self._selected + _PAGE_SIZE)
            event.stop()
            self._refresh()
        elif key == "enter":
            event.stop()
            from .player_detail_screen import PlayerDetailScreen

            self.app.push_screen(
                PlayerDetailScreen(players[self._selected], self._today)
            )
