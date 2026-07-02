"""Selector de jugador para un puesto (o para el banco).

Se abre desde el editor de alineacion (Enter sobre un puesto). Lista el plantel
ORDENADO por aptitud para ese puesto (misma posicion primero, luego la misma
linea, luego el resto; a igualdad, por habilidad) y marca donde esta cada uno
(TIT = titular, BCO = banco). Enter elige; X deja el puesto vacio; Esc cancela.
"""

from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Static

from ...domain.positions import line_of
from ..format import hint
from ..player_labels import POSITION_LABEL
from .base_screen import BaseScreen

_W = 60
_STATUS_STYLE = {"TIT": "bold green", "BCO": "yellow", "": "grey42"}


class PlayerPickerScreen(BaseScreen):
    """Elige un jugador del plantel para un puesto o el banco."""

    BINDINGS = [
        ("escape", "cancel", "Cancelar"),
        ("up", "move(-1)", "Arriba"),
        ("down", "move(1)", "Abajo"),
        ("enter", "pick", "Elegir"),
        ("x", "clear", "Vaciar"),
    ]

    CSS = """
    #viewport { align: center top; }
    #card { width: 62; height: auto; margin-top: 1; }
    #hint { width: 62; text-align: center; color: $text-muted; margin-top: 1; }
    """

    def __init__(self, players, position, status_by_id, on_pick, today) -> None:
        super().__init__()
        self._position = position          # Position del puesto, o None (banco)
        self._status = status_by_id        # id(player) -> "TIT" | "BCO" | ""
        self._on_pick = on_pick
        self._today = today
        self._players = self._sorted(players)
        self._selected = 0

    def _fit_rank(self, player) -> int:
        if self._position is None:
            return 0
        if player.position is self._position:
            return 0
        return 1 if line_of(player.position) is line_of(self._position) else 2

    def _sorted(self, players):
        return sorted(players, key=lambda p: (self._fit_rank(p), -p.overall))

    def compose_viewport(self) -> ComposeResult:
        yield Static(self._card_text(), id="card")
        yield Static(
            hint(("Flechas", "mover"), ("Enter", "elegir"),
                 ("X", "vaciar puesto"), ("Esc", "cancelar")),
            id="hint",
        )

    def _refresh(self) -> None:
        self.query_one("#card", Static).update(self._card_text())

    def _card_text(self) -> Text:
        where = "banco" if self._position is None else POSITION_LABEL[self._position]
        t = Text()
        t.append(f"ELEGIR JUGADOR  -  {where}\n", style="bold green")
        t.append("-" * _W + "\n", style="grey50")
        t.append("   #  NOMBRE                        POS  OVR  EN\n", style="bold green")
        for i, p in enumerate(self._players):
            status = self._status.get(id(p), "")
            row = (f"{str(p.shirt_number or '-'):>3}  {p.full_name:<28.28}  "
                   f"{p.position.value:<3}  {round(p.overall):>3}  ")
            if i == self._selected:
                line = ("> " + row + f"{status:<3}").ljust(_W)
                t.append(line + "\n", style="bold black on green")
            else:
                t.append("  " + row, style="white")
                t.append(f"{status:<3}\n", style=_STATUS_STYLE.get(status, "grey42"))
        return t

    def action_move(self, delta: int) -> None:
        self._selected = max(0, min(len(self._players) - 1, self._selected + delta))
        self._refresh()

    def action_pick(self) -> None:
        if self._players:
            self._on_pick(self._players[self._selected])
        self.app.pop_screen()

    def action_clear(self) -> None:
        self._on_pick(None)
        self.app.pop_screen()

    def action_cancel(self) -> None:
        self.app.pop_screen()
