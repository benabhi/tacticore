"""Pantalla de tactica de UN partido (se abre al elegir un partido en Partidos).

La tactica es POR PARTIDO. Esta es una primera version: deja elegir la mentalidad
y la tactica general y guardarlas en el partido. La parte grande (la cancha con
los 11 titulares y suplentes) se trabaja aparte: es un punto central del
simulador. Por eso aca queda como placeholder claramente marcado.

Teclas: flechas arriba/abajo eligen el campo; izquierda/derecha cambian el valor;
Enter guarda; Esc cancela.
"""

from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Static

from ...domain.enums import Mentality, TeamTactic
from ...domain.tactic import Tactic
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
        ("enter", "save", "Guardar"),
    ]

    CSS = """
    #viewport {
        align: center top;
    }
    #card {
        width: 76;
        height: auto;
        margin-top: 1;
    }
    #hint {
        width: 76;
        text-align: center;
        color: $text-muted;
        margin-top: 1;
    }
    """

    def __init__(self, match, club, on_close=None) -> None:
        super().__init__()
        self._match = match
        self._club = club
        self._on_close = on_close
        # Estado local (no se guarda hasta Enter). Se prellena si ya habia tactica.
        tactic = match.tactic or Tactic()
        self._mentality = _MENTALITIES.index(tactic.mentality)
        self._tactic = _TACTICS.index(tactic.team_tactic)
        self._field = 0  # 0 = mentalidad, 1 = tactica general

    def compose_viewport(self) -> ComposeResult:
        yield Static(self._card_text(), id="card")
        yield Static(
            "Flechas: elegir / cambiar    Enter: guardar    Esc: cancelar",
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

        t.append("  CANCHA Y ALINEACION\n", style="bold green")
        t.append("    Proximamente: colocar los 11 titulares y los suplentes en la\n",
                 style="grey62")
        t.append("    cancha (arrastrando por posicion). Es la parte central que\n",
                 style="grey62")
        t.append("    vamos a trabajar aparte.\n\n", style="grey62")

        t.append("  PLANTEO\n", style="bold green")
        self._field_row(t, 0, "Mentalidad", _MENTALITIES[self._mentality].value)
        self._field_row(t, 1, "Tactica general", _TACTICS[self._tactic].value)
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
            self._mentality = (self._mentality + delta) % len(_MENTALITIES)
        else:
            self._tactic = (self._tactic + delta) % len(_TACTICS)
        self._refresh()

    def action_save(self) -> None:
        self._match.tactic = Tactic(
            mentality=_MENTALITIES[self._mentality],
            team_tactic=_TACTICS[self._tactic],
        )
        if self._on_close is not None:
            self._on_close()
        self.app.pop_screen()

    def action_cancel(self) -> None:
        self.app.pop_screen()
