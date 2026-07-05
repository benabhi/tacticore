"""Seccion Partidos: los encuentros del club.

Pestañas:
- Proximos: los proximos partidos con su FECHA, el tipo (Liga/Amistoso/Copa) y si
  ya tienen tactica asignada. Es una lista navegable: con Enter se abre la
  pantalla de tactica de ESE partido (la tactica es por partido).
- Historial: partidos ya jugados del club.
"""

from datetime import date

from rich.text import Text

from ..format import hint
from .section_screen import SectionScreen

_WIDTH = 78

# Color por tipo de partido (para leer de un vistazo de que competicion es).
_KIND_STYLE = {"Liga": "green", "Amistoso": "grey70", "Copa": "yellow"}

# Columnas de la lista de proximos: (titulo, ancho, alineacion).
_COLUMNS = [
    ("FECHA", 10, "l"), ("TIPO", 9, "l"), ("RIVAL", 30, "l"),
    ("SEDE", 7, "l"), ("TACTICA", 8, "l"),
]


class MatchesScreen(SectionScreen):
    """Proximos partidos (navegables) e historial del club."""

    section_key = "P"
    section_title = "Partidos"
    tabs = ("Proximos", "Historial")

    def __init__(self) -> None:
        super().__init__()
        self._selected = 0  # indice del partido resaltado en Proximos

    @property
    def _club(self):
        game = self.app.game
        return game.player_club if game else None

    @property
    def _league(self):
        game = self.app.game
        return game.player_league if game else None

    def _club_matches(self):
        league, club = self._league, self._club
        if club is None:
            return []
        game = self.app.game
        league_matches = league.matches if league is not None else []
        # Liga + amistosos del jugador, ordenados por fecha (no por jornada: las
        # numeraciones de liga y amistoso se solaparian).
        mine = [m for m in league_matches if m.home is club or m.away is club]
        mine += list(game.friendlies) if game else []
        return sorted(mine, key=lambda m: (m.match_date or date.max, m.matchday))

    def _upcoming(self):
        return [m for m in self._club_matches() if not m.played]

    def render_tab(self, index: int) -> Text:
        if index == 1:
            return self._history_text()
        return self._upcoming_text()

    # --- Proximos (navegable) ---
    def _upcoming_text(self) -> Text:
        club = self._club
        if club is None:
            return Text("Sin club todavia.", style="white")
        upcoming = self._upcoming()
        if not upcoming:
            return Text("No hay proximos partidos.", style="grey62")

        self._selected = max(0, min(len(upcoming) - 1, self._selected))
        t = Text()
        t.append_text(hint(("arr/aba", "elegir partido"), ("Enter", "armar tactica")))
        t.append("\n\n")
        # Encabezado.
        cells = [f"{h:<{w}}" if a == "l" else f"{h:>{w}}" for h, w, a in _COLUMNS]
        t.append("  " + " ".join(cells) + "\n", style="bold green")
        t.append("-" * _WIDTH + "\n", style="grey50")
        for i, m in enumerate(upcoming):
            self._append_match_row(t, m, club, i == self._selected)
        return t

    def _append_match_row(self, t: Text, m, club, selected: bool) -> None:
        when = m.match_date.strftime("%d-%m-%Y") if m.match_date else f"J{m.matchday}"
        rival = m.away if m.home is club else m.home
        sede = "Local" if m.home is club else "Visita"
        has_tactic = m.tactic is not None
        values = [when, m.kind.value, rival.name, sede, "Si" if has_tactic else "No"]
        cells = [
            (str(v)[:w].ljust(w) if a == "l" else str(v)[:w].rjust(w))
            for v, (_, w, a) in zip(values, _COLUMNS)
        ]
        if selected:
            line = ("> " + " ".join(cells)).ljust(_WIDTH)
            t.append(line + "\n", style="bold black on green")
            return
        t.append("  ")
        for i, cell in enumerate(cells):
            title = _COLUMNS[i][0]
            if title == "TIPO":
                style = _KIND_STYLE.get(cell.strip(), "white")
            elif title == "TACTICA":
                style = "green" if cell.strip() == "Si" else "red"
            else:
                style = "white"
            t.append(cell, style=style)
            if i < len(cells) - 1:
                t.append(" ")
        t.append("\n")

    # --- Historial ---
    def _history_text(self) -> Text:
        club = self._club
        played = [m for m in self._club_matches() if m.played] if club else []
        if not played:
            return Text("Todavia no se jugaron partidos.", style="grey62")
        t = Text()
        t.append("Resultados:\n\n", style="grey62")
        for m in played[-16:]:
            rival = m.away if m.home is club else m.home
            gf = m.home_goals if m.home is club else m.away_goals
            gc = m.away_goals if m.home is club else m.home_goals
            res = "G" if gf > gc else "P" if gf < gc else "E"
            style = {"G": "green", "E": "yellow", "P": "red"}[res]
            when = m.match_date.strftime("%d-%m-%Y") if m.match_date else f"J{m.matchday}"
            t.append(f"  {when}  {gf}-{gc}  ", style=style)
            t.append(f"vs {rival.name}\n", style="white")
        return t

    # --- Interaccion (solo en Proximos) ---
    def _move(self, delta: int) -> None:
        total = len(self._upcoming())
        if total:
            self._selected = max(0, min(total - 1, self._selected + delta))
        self._refresh_content()

    def _open_tactic(self) -> None:
        upcoming = self._upcoming()
        if not upcoming:
            return
        from .tactic_screen import TacticScreen

        match = upcoming[self._selected]
        self.app.push_screen(
            TacticScreen(match, self._club, on_close=self._refresh_content)
        )

    def on_content_key(self, event) -> None:
        if self._active_tab != 0:
            return
        key = event.key
        if key == "up":
            event.stop(); self._move(-1)
        elif key == "down":
            event.stop(); self._move(1)
        elif key == "enter":
            event.stop(); self._open_tactic()
