"""Pantalla de tactica de UN partido (se abre al elegir un partido en Partidos).

La tactica es POR PARTIDO y se arma toda en una sola vista de 80x25, en dos
columnas al estilo de la seccion Liga:

- Izquierda, el panel PLANTEO: formacion, mentalidad, tactica general y marcaje
  (campos que se ciclan con las flechas) + un resumen de la alineacion y la info
  del puesto/jugador en foco.
- Derecha, la CANCHA (vista vertical, arco propio abajo) con el DORSAL de cada
  titular en su puesto, y debajo el banco de suplentes.

Se trabaja sobre una copia de la tactica; con `G` se guarda en el partido y con
`Esc` se descarta. `Tab` alterna el foco entre los dos paneles: en PLANTEO las
flechas mueven de campo (arriba/abajo) y cambian su valor (izq/der); en la CANCHA
las flechas mueven de puesto, `Enter` abre el selector de jugador, `X` vacia el
puesto y `A` hace la alineacion automatica.
"""

from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Static

from ... import config
from ...domain.enums import Marking, Mentality, Position, TeamTactic
from ...domain.tactic import Tactic
from ...simulation.match.formation import (
    FORMATIONS, auto_select, get_formation)
from ..format import hint
from ..player_labels import (
    ATTR_GROUPS, ATTR_SHORT, FOOT_SHORT, MORALE_LABEL, POSITION_LABEL)
from .base_screen import BaseScreen

_W = config.SCREEN_WIDTH  # 80
_LW = 38                  # ancho de la columna izquierda (planteo + stats)
_SEP = " | "              # separador vertical entre columnas
_RW = _W - _LW - len(_SEP)   # ancho disponible para la columna derecha (cancha)
_PW, _PH = 35, 17         # ancho y alto de la cancha (vertical)
_PITCH_PAD = (_RW - _PW) // 2   # sangria para centrar la cancha en su columna
_BODY_ROWS = 21           # filas del cuerpo (25 - header - 2 separadores - hint)
_LABEL_W = 11             # ancho de la etiqueta de cada campo del planteo
_FIELD_W = 35             # ancho de la barra resaltada de un campo del planteo
_BENCH = 5                # suplentes en el banco

_MENTALITIES = list(Mentality)
_TACTICS = list(TeamTactic)
_MARKINGS = list(Marking)
_FORMATION_NAMES = [f.name for f in FORMATIONS]


class TacticScreen(BaseScreen):
    """Arma (o edita) la tactica del club del jugador para un partido."""

    CSS = """
    #viewport { align: left top; }
    #card { width: 80; height: 25; }
    """

    def __init__(self, match, club, on_close=None) -> None:
        super().__init__()
        self._match = match
        self._club = club
        self._on_close = on_close
        self._pane = "planteo"  # "planteo" | "cancha"
        self._field = 0         # campo activo del planteo (0..3)
        self._focus = 0         # puesto activo en la cancha (0..n-1 = titulares; n.. = banco)
        # Copia de trabajo (para poder cancelar). Si es nueva, se pre-arma la
        # alineacion automatica asi arranca con un 11 valido.
        src = match.tactic
        if src is not None:
            self._tactic = Tactic(src.mentality, src.team_tactic, src.formation,
                                  list(src.lineup), list(src.bench), src.marking)
        else:
            self._tactic = Tactic()
        if not self._tactic.lineup:
            lineup, bench = auto_select(self._club, get_formation(self._tactic.formation))
            self._tactic.lineup = list(lineup)
            self._tactic.bench = list(bench)
        self._normalize()

    def _normalize(self) -> None:
        """Ajusta el largo de lineup/bench a la formacion y al banco actuales."""
        n = self._n
        self._tactic.lineup = (list(self._tactic.lineup) + [None] * n)[:n]
        self._tactic.bench = (list(self._tactic.bench) + [None] * _BENCH)[:_BENCH]
        self._focus = min(self._focus, n + _BENCH - 1)

    # --- Formacion y slots ---
    @property
    def _formation(self):
        return get_formation(self._tactic.formation)

    @property
    def _slots(self):
        return self._formation.slots

    @property
    def _n(self) -> int:
        return len(self._slots)

    # --- Acceso unificado a puestos (titulares + banco) ---
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
        yield Static(self._content_text(), id="card")

    def _refresh(self) -> None:
        self.query_one("#card", Static).update(self._content_text())

    def _content_text(self) -> Text:
        t = Text(no_wrap=True)
        t.append_text(self._header_line())
        t.append("\n")
        t.append("-" * _W + "\n", style="grey50")
        left = self._left_lines()
        right = self._right_lines()
        for i in range(_BODY_ROWS):
            lline = left[i] if i < len(left) else Text("")
            rline = right[i] if i < len(right) else Text("")
            t.append_text(lline)
            t.append(" " * max(0, _LW - len(lline.plain)))
            t.append(_SEP, style="grey50")
            t.append_text(rline)
            t.append("\n")
        t.append("-" * _W + "\n", style="grey50")
        t.append_text(self._hint_line())
        return t

    def _header_line(self) -> Text:
        m, club = self._match, self._club
        rival = m.away if m.home is club else m.home
        sede = "Local" if m.home is club else "Visitante"
        when = m.match_date.strftime("%d-%m-%Y") if m.match_date else f"J{m.matchday}"
        t = Text(no_wrap=True)
        t.append("TACTICA DEL PARTIDO", style="bold green")
        t.append(f"  J{m.matchday} {when} - {m.kind.value}  ", style="grey62")
        t.append(f"vs {rival.name[:16]} ({sede})", style="bold white")
        return t

    def _hint_line(self) -> Text:
        return hint(("Tab", "panel"), ("Flechas", "mover"), ("Enter", "elegir"),
                    ("X", "quitar"), ("A", "auto"), ("G", "guardar"),
                    ("Esc", "salir"), sep=" ")

    def _panel_title(self, label: str, pane: str) -> Text:
        """Titulo de panel con efecto pestaña: activo = fondo verde/letra negra;
        inactivo = sin fondo, letra verde (como todos los titulos de la app)."""
        if self._pane == pane:
            return Text(f" {label} ", style="bold black on green")
        return Text(label, style="bold green")

    # --- Columna izquierda: planteo (arriba) + stats del jugador (abajo) ---
    def _left_lines(self) -> list[Text]:
        lines = [self._panel_title("PLANTEO", "planteo")]
        lines.append(self._field_row(0, "Formacion", self._tactic.formation))
        lines.append(self._field_row(1, "Mentalidad", self._tactic.mentality.value))
        lines.append(self._field_row(2, "Tactica", self._tactic.team_tactic.value))
        lines.append(self._field_row(3, "Marcaje", self._tactic.marking.value))
        lines.append(Text("-" * _LW, style="grey50"))  # divide planteo / stats
        lines.extend(self._stats_lines())
        return lines

    def _field_row(self, index: int, label: str, value: str) -> Text:
        active = self._pane == "planteo"
        selected = active and index == self._field
        text = f" {label:<{_LABEL_W}} < {value} >"
        if selected:  # campo elegido: barra verde (mismo efecto que las pestañas)
            return Text(text.ljust(_FIELD_W), style="bold black on green")
        return Text(text[:_LW], style="white" if active else "grey50")

    # --- Stats resumidas del jugador en foco (parte baja de la columna izq) ---
    @staticmethod
    def _attr_style(value: float) -> str:
        """Color rapido por nivel del atributo (verde alto, gris bajo)."""
        if value >= 70:
            return "green"
        if value >= 50:
            return "white"
        return "grey62"

    def _attr_line(self, player, attrs) -> Text:
        t = Text("  ", no_wrap=True)
        for i, attr in enumerate(attrs):
            if i:
                t.append(" ")
            value = getattr(player, attr)
            t.append(ATTR_SHORT[attr], style="grey50")
            t.append(f"{round(value):>3}", style=self._attr_style(value))
        return t

    def _stats_lines(self) -> list[Text]:
        idx = self._focus
        player = self._get(idx)
        if idx < self._n:
            where = "Puesto: " + POSITION_LABEL[self._slots[idx].position]
        else:
            where = f"Banco (suplente {idx - self._n + 1})"
        lines = [Text(where[:_LW], style="bold green")]
        if player is None:
            lines.append(Text("  (vacio)", style="grey42"))
            return lines
        today = self._club_today()
        age = f"{player.age_on(today)}a" if today else "--"
        lines.append(Text(f"  {player.shirt_number or '-'} {player.full_name}"[:_LW],
                          style="bold white"))
        lines.append(Text(f"  {player.position.value}  {FOOT_SHORT[player.foot]}  "
                          f"{age}  OVR {round(player.overall)}", style="grey62"))
        lines.append(Text(f"  Forma {round(player.form)}  Fis {round(player.fitness)}  "
                          f"{MORALE_LABEL[player.morale]}", style="grey62"))
        for name, attrs in ATTR_GROUPS:
            lines.append(Text(name, style="grey70"))
            lines.append(self._attr_line(player, attrs))
        return lines

    # --- Columna derecha: cabecera (cancha + resumen) + cancha + banco ---
    def _right_lines(self) -> list[Text]:
        starters = sum(1 for p in self._tactic.lineup if p is not None)
        bench = sum(1 for p in self._tactic.bench if p is not None)
        head = self._indent(self._panel_title("CANCHA", "cancha"))
        head.append(f"  {starters}/{self._n} titulares  {bench}/{_BENCH} banco",
                    style="grey62")
        lines = [head]
        for row in self._pitch_lines():
            lines.append(self._indent(row))
        lines.append(Text(""))
        lines.append(self._bench_line())
        return lines

    @staticmethod
    def _indent(line: Text) -> Text:
        out = Text(" " * _PITCH_PAD)
        out.append_text(line)
        return out

    def _shirt(self, idx) -> str:
        p = self._get(idx)
        return "--" if p is None else f"{(p.shirt_number or 0):>2}"

    def _marker_style(self, idx, is_gk: bool) -> str:
        if self._pane == "cancha" and idx == self._focus:
            return "bold black on yellow"
        if self._get(idx) is None:
            return "grey42"
        return "bold magenta" if is_gk else "bold cyan"

    def _pitch_lines(self) -> list[Text]:
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

        lines = []
        for r in range(_PH):
            line = Text(no_wrap=True)
            c = 0
            while c < _PW:
                st = style[r][c]
                buf = char[r][c]
                c += 1
                while c < _PW and style[r][c] == st:
                    buf += char[r][c]
                    c += 1
                line.append(buf) if st is None else line.append(buf, style=st)
            lines.append(line)
        return lines

    def _bench_line(self) -> Text:
        t = Text(" " * _PITCH_PAD)
        t.append("Banco: ", style="bold green")
        for j in range(_BENCH):
            idx = self._n + j
            t.append(f"[{self._shirt(idx)}]", style=self._marker_style(idx, False))
            t.append(" ")
        return t

    # --- Teclado (contextual segun panel activo) ---
    def on_key(self, event) -> None:
        key = event.key
        if key == "g":
            event.stop(); self._save(); return
        if key == "escape":
            event.stop(); self.app.pop_screen(); return
        if key in ("tab", "shift+tab"):
            event.stop(); self._toggle_pane(); return
        if self._pane == "planteo":
            self._key_planteo(event)
        else:
            self._key_cancha(event)

    def _toggle_pane(self) -> None:
        self._pane = "cancha" if self._pane == "planteo" else "planteo"
        self._refresh()

    def _key_planteo(self, event) -> None:
        key = event.key
        if key == "up":
            event.stop(); self._field = (self._field - 1) % 4; self._refresh()
        elif key == "down":
            event.stop(); self._field = (self._field + 1) % 4; self._refresh()
        elif key == "left":
            event.stop(); self._change_value(-1)
        elif key == "right":
            event.stop(); self._change_value(1)

    def _key_cancha(self, event) -> None:
        key = event.key
        if key in ("up", "down", "left", "right"):
            event.stop()
            delta = -1 if key in ("up", "left") else 1
            self._focus = (self._focus + delta) % (self._n + _BENCH)
            self._refresh()
        elif key == "enter":
            event.stop(); self._choose()
        elif key == "x":
            event.stop(); self._assign(self._focus, None); self._refresh()
        elif key == "a":
            event.stop(); self._auto()

    # --- Acciones del planteo ---
    def _change_value(self, delta: int) -> None:
        if self._field == 0:
            self._change_formation(delta)
        elif self._field == 1:
            cur = _MENTALITIES.index(self._tactic.mentality)
            self._tactic.mentality = _MENTALITIES[(cur + delta) % len(_MENTALITIES)]
        elif self._field == 2:
            cur = _TACTICS.index(self._tactic.team_tactic)
            self._tactic.team_tactic = _TACTICS[(cur + delta) % len(_TACTICS)]
        else:
            cur = _MARKINGS.index(self._tactic.marking)
            self._tactic.marking = _MARKINGS[(cur + delta) % len(_MARKINGS)]
        self._refresh()

    def _change_formation(self, delta: int) -> None:
        name = self._tactic.formation
        cur = _FORMATION_NAMES.index(name) if name in _FORMATION_NAMES else 0
        self._tactic.formation = _FORMATION_NAMES[(cur + delta) % len(_FORMATION_NAMES)]
        # Cambiar de formacion re-arma la alineacion automatica para la nueva forma
        # (los ajustes manuales previos se pierden: la cantidad de puestos cambia).
        lineup, bench = auto_select(self._club, self._formation)
        self._tactic.lineup = list(lineup)
        self._tactic.bench = list(bench)
        self._normalize()

    # --- Acciones de la cancha ---
    def _choose(self) -> None:
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
            self._club.players, position, status, self._on_pick, self._club_today(),
        ))

    def _club_today(self):
        game = self.app.game
        return game.calendar.current_date if game else None

    def _on_pick(self, player) -> None:
        self._assign(self._focus, player)
        self._refresh()

    def _auto(self) -> None:
        lineup, bench = auto_select(self._club, self._formation, _BENCH)
        for i in range(self._n):
            self._tactic.lineup[i] = lineup[i] if i < len(lineup) else None
        for j in range(_BENCH):
            self._tactic.bench[j] = bench[j] if j < len(bench) else None
        self._refresh()

    # --- Guardar / cancelar ---
    def _save(self) -> None:
        self._match.tactic = self._tactic
        if self._on_close is not None:
            self._on_close()
        self.app.pop_screen()
