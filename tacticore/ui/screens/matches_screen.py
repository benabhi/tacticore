"""Seccion Partidos: los encuentros del club y la tactica.

Pestañas:
- Proximos: los proximos partidos, con el TIPO marcado (Liga/Amistoso/Copa) y el
  siguiente resaltado.
- Tactica: formacion/instrucciones + presets (placeholder).
- Historial: partidos ya jugados del club.
"""

from rich.text import Text

from ..format import append_section
from .section_screen import SectionScreen

# Color por tipo de partido (para leer de un vistazo de que competicion es).
_KIND_STYLE = {"Liga": "green", "Amistoso": "grey70", "Copa": "yellow"}


class MatchesScreen(SectionScreen):
    """Proximos partidos, tactica e historial del club."""

    section_key = "P"
    section_title = "Partidos"
    tabs = ("Proximos", "Tactica", "Historial")

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
        if league is None or club is None:
            return []
        return sorted(
            (m for m in league.matches if m.home is club or m.away is club),
            key=lambda m: m.matchday,
        )

    def render_tab(self, index: int) -> Text:
        if index == 1:
            return self._tactics_text()
        if index == 2:
            return self._history_text()
        return self._upcoming_text()

    def _upcoming_text(self) -> Text:
        club = self._club
        if club is None:
            return Text("Sin club todavia.", style="white")
        upcoming = [m for m in self._club_matches() if not m.played]
        if not upcoming:
            return Text("No hay proximos partidos.", style="grey62")

        t = Text()
        t.append("Proximos partidos:\n\n", style="grey62")
        for i, m in enumerate(upcoming[:16]):
            rival = m.away if m.home is club else m.home
            sede = "L" if m.home is club else "V"
            marker = "> " if i == 0 else "  "
            row = (f"{marker}J{m.matchday:<2}  ")
            t.append(row, style="bold white" if i == 0 else "white")
            t.append(f"{m.kind.value:<9}", style=_KIND_STYLE.get(m.kind.value, "white"))
            t.append(f"[{sede}] vs {rival.name}\n",
                     style="bold white" if i == 0 else "white")
        return t

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
            t.append(f"  J{m.matchday:<2}  {gf}-{gc}  ", style=style)
            t.append(f"vs {rival.name}\n", style="white")
        return t

    def _tactics_text(self) -> Text:
        t = Text()
        append_section(t, "TACTICA", [
            ("Sin tactica asignada para el proximo partido.", "grey62"),
            "",
            ("Aca vas a poder definir por partido:", "grey62"),
            ("  - Formacion (ej. 4-3-3) y los 11 titulares", "grey70"),
            ("  - Instrucciones de equipo (presion, ritmo, linea)", "grey70"),
            ("  - Guardar presets y reusarlos en otros partidos", "grey70"),
        ])
        return t
