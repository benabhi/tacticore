"""Editor de alineacion: la cancha con los titulares y el banco.

Se abre desde la pantalla de Tactica. Muestra la cancha (vista de arriba, el arco
propio abajo) con el DORSAL de cada titular en su puesto. Se navega los puestos
con las flechas; Enter abre el selector de jugador; X vacia el puesto; A hace la
alineacion automatica (por posicion preferida y habilidad); Esc vuelve. Debajo, el
banco de suplentes (extras), que se edita igual.

Opera sobre la `Tactic` del partido (in-place): `lineup` (titulares alineados a
los slots) y `bench` (suplentes).
"""

from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Static

from ...domain.enums import Position
from ...simulation.match.formation import auto_select, get_formation
from ..player_labels import POSITION_LABEL
from .base_screen import BaseScreen

_PW, _PH = 52, 15   # ancho y alto de la cancha (interior con borde)
_BENCH = 5          # cantidad de suplentes en el banco
_CARD_W = 76


class LineupScreen(BaseScreen):
    """Arma los 11 titulares (sobre la cancha) y el banco de suplentes."""

    BINDINGS = [
        ("escape", "back", "Volver"),
        ("up", "move(-1)", "Anterior"),
        ("left", "move(-1)", "Anterior"),
        ("down", "move(1)", "Siguiente"),
        ("right", "move(1)", "Siguiente"),
        ("enter", "choose", "Elegir"),
        ("x", "clear", "Vaciar"),
        ("a", "auto", "Automatica"),
    ]

    CSS = """
    #viewport { align: center top; }
    #card { width: 76; height: auto; margin-top: 1; }
    #hint { width: 76; text-align: center; color: $text-muted; margin-top: 1; }
    """

    def __init__(self, tactic, club, on_close=None) -> None:
        super().__init__()
        self._tactic = tactic
        self._club = club
        self._on_close = on_close
        self._formation = get_formation(tactic.formation)
        self._slots = self._formation.slots
        # Normalizar largos de lineup/bench a la formacion y al banco.
        n = len(self._slots)
        tactic.lineup = (list(tactic.lineup) + [None] * n)[:n]
        tactic.bench = (list(tactic.bench) + [None] * _BENCH)[:_BENCH]
        self._focus = 0  # 0..n-1 = puestos; n..n+_BENCH-1 = banco

    # --- Acceso unificado a puestos (titulares + banco) ---
    @property
    def _n(self) -> int:
        return len(self._slots)

    def _get(self, idx):
        return self._tactic.lineup[idx] if idx < self._n else self._tactic.bench[idx - self._n]

    def _set(self, idx, player) -> None:
        if idx < self._n:
            self._tactic.lineup[idx] = player
        else:
            self._tactic.bench[idx - self._n] = player

    def _find(self, player):
        for i in range(self._n + _BENCH):
            if self._get(i) is player:
                return i
        return None

    def _assign(self, idx, player) -> None:
        """Pone `player` en el puesto `idx` (None = vaciar), con swap si hace falta."""
        if player is None:
            self._set(idx, None)
            return
        src = self._find(player)
        old = self._get(idx)
        self._set(idx, player)
        if src is not None and src != idx:
            self._set(src, old)   # estaba en otro puesto -> intercambio

    # --- Composicion ---
    def compose_viewport(self) -> ComposeResult:
        yield Static(self._card_text(), id="card")
        yield Static(
            "Flechas: mover   Enter: elegir   X: quitar   A: automatica   Esc: volver",
            id="hint",
        )

    def _refresh(self) -> None:
        self.query_one("#card", Static).update(self._card_text())

    def _shirt(self, idx) -> str:
        p = self._get(idx)
        if p is None:
            return "--"
        return f"{(p.shirt_number or 0):>2}"

    def _marker_style(self, idx, is_gk: bool) -> str:
        if idx == self._focus:
            return "bold black on yellow"
        if self._get(idx) is None:
            return "grey42"
        return "bold magenta" if is_gk else "bold cyan"

    def _card_text(self) -> Text:
        t = Text()
        # Encabezado.
        starters = sum(1 for p in self._tactic.lineup if p is not None)
        head = "ALINEACION"
        info = f"Formacion: {self._formation.name}    Titulares: {starters}/{self._n}"
        t.append(" " + head, style="bold green")
        t.append(" " * max(1, _CARD_W - 1 - len(head) - len(info)))
        t.append(info + "\n", style="grey62")

        # Cancha con los dorsales.
        self._append_pitch(t)

        # Banco.
        t.append("\n  Suplentes:  ", style="bold green")
        for j in range(_BENCH):
            idx = self._n + j
            t.append(f"[{self._shirt(idx)}]", style=self._marker_style(idx, False))
            t.append(" ")
        t.append("\n")

        # Info del puesto en foco.
        t.append(self._focus_info(), style="white")
        return t

    def _append_pitch(self, t: Text) -> None:
        char = [[" "] * _PW for _ in range(_PH)]
        style: list[list] = [[None] * _PW for _ in range(_PH)]

        def put(r, c, ch, st):
            if 0 <= r < _PH and 0 <= c < _PW:
                char[r][c] = ch
                style[r][c] = st

        # Borde y linea de mitad de cancha (verde).
        for c in range(_PW):
            put(0, c, "-", "green"); put(_PH - 1, c, "-", "green")
        for r in range(_PH):
            put(r, 0, "|", "green"); put(r, _PW - 1, "|", "green")
        for r, c in ((0, 0), (0, _PW - 1), (_PH - 1, 0), (_PH - 1, _PW - 1)):
            put(r, c, "+", "green")
        mid = _PH // 2
        for c in range(1, _PW - 1):
            if char[mid][c] == " ":
                put(mid, c, "-", "green")
        # Arcos (arriba = rival, abajo = propio).
        gc = _PW // 2
        for c in (gc - 1, gc, gc + 1):
            put(0, c, "=", "white"); put(_PH - 1, c, "=", "white")

        # Marcadores de cada puesto (dorsal), ubicados por rel_x/rel_y.
        for i, slot in enumerate(self._slots):
            r = round((1.0 - slot.rel_x) * (_PH - 1))
            c = round(slot.rel_y * (_PW - 1))
            r = max(1, min(_PH - 2, r))
            start = max(1, min(_PW - 3, c - 1))
            marker = self._shirt(i)
            st = self._marker_style(i, slot.position is Position.GOALKEEPER)
            put(r, start, marker[0], st)
            put(r, start + 1, marker[1], st)

        pad = " " * ((_CARD_W - _PW) // 2)
        for r in range(_PH):
            t.append(pad)
            c = 0
            while c < _PW:
                st = style[r][c]
                buf = char[r][c]
                c += 1
                while c < _PW and style[r][c] == st:
                    buf += char[r][c]
                    c += 1
                t.append(buf) if st is None else t.append(buf, style=st)
            t.append("\n")

    def _focus_info(self) -> str:
        idx = self._focus
        player = self._get(idx)
        who = "vacio" if player is None else \
            f"{player.shirt_number or '-'} {player.full_name} ({player.position.value}, OVR {round(player.overall)})"
        if idx < self._n:
            puesto = POSITION_LABEL[self._slots[idx].position]
            return f"  > Puesto: {puesto:<24} {who}"
        return f"  > Banco (suplente {idx - self._n + 1}):  {who}"

    # --- Acciones ---
    def action_move(self, delta: int) -> None:
        self._focus = (self._focus + delta) % (self._n + _BENCH)
        self._refresh()

    def action_choose(self) -> None:
        from .player_picker_screen import PlayerPickerScreen

        idx = self._focus
        position = self._slots[idx].position if idx < self._n else None
        status = {}
        for p in self._tactic.lineup:
            if p is not None:
                status[id(p)] = "TIT"
        for p in self._tactic.bench:
            if p is not None:
                status[id(p)] = "BCO"
        self.app.push_screen(PlayerPickerScreen(
            self._club.players, position, status, self._on_pick,
            self._club_today(),
        ))

    def _club_today(self):
        game = self.app.game
        return game.calendar.current_date if game else None

    def _on_pick(self, player) -> None:
        self._assign(self._focus, player)
        self._refresh()

    def action_clear(self) -> None:
        self._assign(self._focus, None)
        self._refresh()

    def action_auto(self) -> None:
        lineup, bench = auto_select(self._club, self._formation, _BENCH)
        for i in range(self._n):
            self._tactic.lineup[i] = lineup[i] if i < len(lineup) else None
        for j in range(_BENCH):
            self._tactic.bench[j] = bench[j] if j < len(bench) else None
        self._refresh()

    def action_back(self) -> None:
        if self._on_close is not None:
            self._on_close()
        self.app.pop_screen()
