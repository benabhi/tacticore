"""Seccion Entreno: entrenamiento por habilidad, con grupos de jugadores.

Pestañas:
- Grupos: grupos de entrenamiento, cada uno enfocado en una habilidad entrenable,
  con varios jugadores asignados (placeholder; el sistema real llega despues).
- Historial: resultados de entrenamientos por semana (placeholder).

El objetivo (a diferencia de Hattrick) es poder entrenar CADA habilidad del juego
y agrupar mas de un jugador en cada foco de entrenamiento.
"""

from rich.text import Text

from ...domain.player import MENTAL_ATTRS, PHYSICAL_ATTRS, TECHNICAL_ATTRS
from ..format import append_section
from ..player_labels import ATTR_LABEL
from .section_screen import SectionScreen


class TrainingScreen(SectionScreen):
    """Grupos de entrenamiento por habilidad e historial."""

    section_key = "E"
    section_title = "Entreno"
    tabs = ("Grupos", "Historial")

    def render_tab(self, index: int) -> Text:
        if index == 1:
            return self._history_text()
        return self._groups_text()

    def _groups_text(self) -> Text:
        t = Text()
        t.append("Vas a poder armar grupos de entrenamiento, cada uno enfocado en\n",
                 style="grey62")
        t.append("una habilidad, con varios jugadores adentro. Habilidades entrenables:\n\n",
                 style="grey62")
        # Las 15 habilidades entrenables, agrupadas por categoria (3 columnas).
        groups = [
            ("FISICO", PHYSICAL_ATTRS),
            ("TECNICO", TECHNICAL_ATTRS),
            ("MENTAL", MENTAL_ATTRS),
        ]
        col_w = 26
        for title, _attrs in groups:
            t.append(title.ljust(col_w), style="bold green")
        t.append("\n")
        for i in range(5):
            for _title, attrs in groups:
                label = ATTR_LABEL[attrs[i]] if i < len(attrs) else ""
                t.append(("  " + label).ljust(col_w), style="grey70")
            t.append("\n")
        t.append("\n")
        t.append("Proximamente: crear grupos, asignar jugadores e intensidad.",
                 style="grey62")
        return t

    def _history_text(self) -> Text:
        t = Text()
        append_section(t, "HISTORIAL DE ENTRENAMIENTO", [
            ("Todavia no hay entrenamientos registrados.", "grey62"),
            "",
            ("El entrenamiento se resolvera en un dia fijo de la semana", "grey62"),
            ("(ver Oficina > Semana) y sus resultados se listaran aca.", "grey62"),
        ])
        return t
