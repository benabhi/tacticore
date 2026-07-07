"""Asignar jugadores al grupo de entrenamiento de un atributo (modal).

Se abre desde Entrenamiento > Grupos con Enter sobre un atributo. Lista el plantel;
cada jugador puede estar ENTRENANDO ESTE atributo, otro, o ninguno (foco EXCLUSIVO:
asignar a este lo saca del anterior). Muestra el valor actual del atributo / potencial
y si todavia puede subir (bajo el techo de capacidad). Esc guarda y vuelve.
"""

from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Static

from ...persistence import savegame
from ...simulation import training as tr
from ..format import hint
from ..player_labels import ATTR_LABEL
from .base_screen import BaseScreen

_W = 76
_PAGE = 15  # jugadores por pagina


class TrainingAssignScreen(BaseScreen):
    """Asigna/saca jugadores del grupo de entrenamiento de un atributo."""

    BINDINGS = [
        ("escape", "close", "Volver"),
        ("up", "move(-1)", "Arriba"),
        ("down", "move(1)", "Abajo"),
        ("left", "page(-1)", "Pagina"),
        ("right", "page(1)", "Pagina"),
        ("space", "toggle", "Asignar"),
        ("enter", "toggle", "Asignar"),
    ]

    CSS = """
    #viewport { align: center top; }
    #card { width: 78; height: auto; margin-top: 1; }
    #hint { width: 78; text-align: center; color: $text-muted; margin-top: 1; }
    """

    def __init__(self, game, attr: str, on_close=None) -> None:
        super().__init__()
        self._game = game
        self._attr = attr
        self._on_close = on_close
        self._sel = 0

    @property
    def _players(self):
        return self._game.player_club.players

    def compose_viewport(self) -> ComposeResult:
        yield Static(self._card_text(), id="card")
        yield Static(
            hint(("^v", "mover"), ("izq/der", "pagina"), ("Espacio", "asignar/sacar"),
                 ("Esc", "volver"), sep="  "),
            id="hint",
        )

    def _refresh(self) -> None:
        self.query_one("#card", Static).update(self._card_text())

    def _card_text(self) -> Text:
        club = self._game.player_club
        today = self._game.calendar.current_date
        cap = tr.capacity(club)
        players = self._players
        self._sel = max(0, min(len(players) - 1, self._sel))
        pages = max(1, (len(players) + _PAGE - 1) // _PAGE)
        page = self._sel // _PAGE
        rows = list(enumerate(players))[page * _PAGE: page * _PAGE + _PAGE]

        t = Text()
        t.append(f"ENTRENAR: {ATTR_LABEL[self._attr]}", style="bold green")
        t.append(f"   Capacidad {cap:.0f}   ({len(tr.group_for(club, self._attr))} en el grupo)",
                 style="grey70")
        if pages > 1:
            t.append(f"   Pag {page + 1}/{pages}", style="grey62")
        t.append("\n")
        t.append("-" * _W + "\n", style="grey50")
        for i, p in rows:
            self._append_row(t, i, p, cap, today, i == self._sel)
        return t

    def _append_row(self, t: Text, i: int, p, cap: float, today, selected: bool) -> None:
        val = getattr(p, self._attr)
        if p.training_focus == self._attr:
            tag = "ENTRENA ESTO"
        elif p.training_focus:
            tag = ATTR_LABEL[p.training_focus]
        else:
            tag = "libre"
        room = "" if tr.can_improve(p, self._attr, cap) else "tope"
        row = (f"{p.full_name:<20.20} {p.position.value:<3} {val:>4.1f}/{p.potential:<2.0f} "
               f"{room:<4} {tag}")
        if selected:
            t.append(("> " + row)[:_W].ljust(_W) + "\n", style="bold black on green")
            return
        style = ("bold green" if p.training_focus == self._attr
                 else "yellow" if p.training_focus else "grey62")
        t.append("  " + row[:_W - 2] + "\n", style=style)

    def action_move(self, delta: int) -> None:
        self._sel = max(0, min(len(self._players) - 1, self._sel + delta))
        self._refresh()

    def action_page(self, delta: int) -> None:
        self._sel = max(0, min(len(self._players) - 1, self._sel + delta * _PAGE))
        self._refresh()

    def action_toggle(self) -> None:
        p = self._players[self._sel]
        if p.training_focus == self._attr:
            tr.clear(p)
        else:
            tr.assign(p, self._attr)
        self._refresh()

    def action_close(self) -> None:
        savegame.save_game(self._game)
        if self._on_close is not None:
            self._on_close()
        self.app.pop_screen()
