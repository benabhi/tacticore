"""Seccion Jugadores: la plantilla del club en una tabla paginada.

Muestra una fila por jugador con los datos esenciales (no todos: no entran). Se
navega con las flechas (arriba/abajo entre filas, izquierda/derecha entre
paginas) y con Enter se abre la ficha completa del jugador. Todo en 80x25.
"""

from collections.abc import Iterator

from rich.text import Text
from textual.widget import Widget
from textual.widgets import Static

from ..player_labels import FOOT_SHORT, POSITION_SHORT
from .section_screen import SectionScreen

_PAGE_SIZE = 14  # filas de jugadores por pagina

# Columnas de la tabla: (titulo, ancho). El nombre se lleva el grueso del ancho.
_COLUMNS = [
    ("#", 2), ("NOMBRE", 22), ("POS", 3), ("NAC", 3), ("ED", 3),
    ("PIE", 3), ("OVR", 3), ("POT", 3), ("FOR", 3), ("FIT", 3),
]


class PlayersScreen(SectionScreen):
    """Plantilla del club: tabla paginada y navegable."""

    section_key = "J"

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
        # Encabezado de columnas.
        t.append("  " + self._row_cells(_COLUMNS) + "\n", style="bold green")
        t.append("  " + "-" * (sum(w for _, w in _COLUMNS) + len(_COLUMNS) - 1) + "\n",
                 style="grey50")
        # Filas de jugadores.
        for offset, player in enumerate(page_players):
            idx = start + offset
            line = self._player_cells(idx, player)
            if idx == self._selected:
                t.append("> ", style="bold black on green")
                t.append(line + "\n", style="bold black on green")
            else:
                t.append("  ")
                t.append(line + "\n", style="white")
        # Relleno para que el pie quede en su lugar aunque la pagina este corta.
        for _ in range(_PAGE_SIZE - len(page_players)):
            t.append("\n")
        # Pie: indicadores de teclas + paginacion.
        t.append("\n")
        t.append("Flechas: mover   Enter: ficha   <- ->: pagina", style="grey62")
        t.append(f"        Pagina {page + 1}/{pages}\n", style="grey62")
        return t

    def _row_cells(self, cells) -> str:
        """Une celdas (texto, ancho) con un espacio; numeros a la derecha."""
        right = {"#", "ED", "OVR", "POT", "FOR", "FIT"}
        parts = []
        for title, width in cells:
            text = str(title)[:width]
            parts.append(text.rjust(width) if title in right else text.ljust(width))
        return " ".join(parts)

    def _player_cells(self, idx: int, p) -> str:
        values = [
            (str(p.shirt_number or "-"), 2, True),
            (p.full_name, 22, False),
            (POSITION_SHORT[p.position], 3, False),
            (p.nationality, 3, False),
            (str(p.age_on(self._today)), 3, True),
            (FOOT_SHORT[p.foot], 3, False),
            (str(round(p.overall)), 3, True),
            (str(round(p.potential)), 3, True),
            (str(round(p.form)), 3, True),
            (str(round(p.fitness)), 3, True),
        ]
        parts = []
        for text, width, right in values:
            text = text[:width]
            parts.append(text.rjust(width) if right else text.ljust(width))
        return " ".join(parts)

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
