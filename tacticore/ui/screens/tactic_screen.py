"""Pantalla de tactica de UN partido (se abre al elegir un partido en Partidos).

La tactica es POR PARTIDO. Aca se define el planteo (mentalidad y tactica general)
y se accede al editor de ALINEACION (la cancha con los 11 titulares y el banco),
que es una pantalla aparte. Se trabaja sobre una copia de la tactica; con Enter se
guarda en el partido y con Esc se descarta.

Teclas: flechas arriba/abajo eligen el campo del planteo; izquierda/derecha
cambian el valor; F abre la alineacion; Enter guarda; Esc cancela.
"""

from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Static

from ...domain.enums import Mentality, TeamTactic
from ...domain.tactic import Tactic
from ...simulation.match.formation import auto_select, get_formation
from .base_screen import BaseScreen

_W = 76
_MENTALITIES = list(Mentality)
_TACTICS = list(TeamTactic)


class TacticScreen(BaseScreen):
    """Arma (o edita) la tactica del club del jugador para un partido."""

    BINDINGS = [
        ("escape", "cancel", "Cancelar"),
        ("up", "prev_field", "Arriba"),
        ("down", "next_field", "Abajo"),
        ("left", "change(-1)", "Menos"),
        ("right", "change(1)", "Mas"),
        ("f", "lineup", "Alineacion"),
        ("enter", "save", "Guardar"),
    ]

    CSS = """
    #viewport { align: center top; }
    #card { width: 76; height: auto; margin-top: 1; }
    #hint { width: 76; text-align: center; color: $text-muted; margin-top: 1; }
    """

    def __init__(self, match, club, on_close=None) -> None:
        super().__init__()
        self._match = match
        self._club = club
        self._on_close = on_close
        self._field = 0  # 0 = mentalidad, 1 = tactica general
        # Copia de trabajo (para poder cancelar). Si es nueva, se pre-arma la
        # alineacion automatica asi arranca con un 11 valido.
        src = match.tactic
        if src is not None:
            self._tactic = Tactic(src.mentality, src.team_tactic, src.formation,
                                  list(src.lineup), list(src.bench))
        else:
            self._tactic = Tactic()
        if not self._tactic.lineup:
            lineup, bench = auto_select(self._club, get_formation(self._tactic.formation))
            self._tactic.lineup = list(lineup)
            self._tactic.bench = list(bench)

    def compose_viewport(self) -> ComposeResult:
        yield Static(self._card_text(), id="card")
        yield Static(
            "Flechas: planteo   F: alineacion   Enter: guardar   Esc: cancelar",
            id="hint",
        )

    def _refresh(self) -> None:
        self.query_one("#card", Static).update(self._card_text())

    def _card_text(self) -> Text:
        m, club = self._match, self._club
        rival = m.away if m.home is club else m.home
        sede = "Local" if m.home is club else "Visitante"
        when = m.match_date.strftime("%d-%m-%Y") if m.match_date else f"Jornada {m.matchday}"

        t = Text()
        t.append("TACTICA DEL PARTIDO\n", style="bold green")
        t.append("-" * _W + "\n", style="grey50")
        t.append(f"  Jornada {m.matchday}  -  {when}  -  {m.kind.value}\n", style="white")
        t.append(f"  vs {rival.name}  ({sede})\n\n", style="bold white")

        # Alineacion (resumen + acceso al editor).
        starters = sum(1 for p in self._tactic.lineup if p is not None)
        bench = sum(1 for p in self._tactic.bench if p is not None)
        t.append("  ALINEACION\n", style="bold green")
        t.append(f"    Formacion {self._tactic.formation}   "
                 f"{starters}/{len(self._tactic.lineup)} titulares, {bench} en el banco\n",
                 style="white")
        t.append("    F: abrir la cancha para elegir jugadores y suplentes\n\n",
                 style="grey62")

        # Planteo.
        t.append("  PLANTEO\n", style="bold green")
        self._field_row(t, 0, "Mentalidad", self._tactic.mentality.value)
        self._field_row(t, 1, "Tactica general", self._tactic.team_tactic.value)
        return t

    def _field_row(self, t: Text, index: int, label: str, value: str) -> None:
        selected = index == self._field
        marker = "> " if selected else "  "
        style = "bold black on green" if selected else "white"
        line = f"{marker}{label + ':':<18}< {value} >"
        t.append("  " + line + "\n", style=style)

    # --- Acciones ---
    def action_prev_field(self) -> None:
        self._field = (self._field - 1) % 2
        self._refresh()

    def action_next_field(self) -> None:
        self._field = (self._field + 1) % 2
        self._refresh()

    def action_change(self, delta: int) -> None:
        if self._field == 0:
            cur = _MENTALITIES.index(self._tactic.mentality)
            self._tactic.mentality = _MENTALITIES[(cur + delta) % len(_MENTALITIES)]
        else:
            cur = _TACTICS.index(self._tactic.team_tactic)
            self._tactic.team_tactic = _TACTICS[(cur + delta) % len(_TACTICS)]
        self._refresh()

    def action_lineup(self) -> None:
        from .lineup_screen import LineupScreen

        self.app.push_screen(LineupScreen(self._tactic, self._club, on_close=self._refresh))

    def action_save(self) -> None:
        self._match.tactic = self._tactic
        if self._on_close is not None:
            self._on_close()
        self.app.pop_screen()

    def action_cancel(self) -> None:
        self.app.pop_screen()
