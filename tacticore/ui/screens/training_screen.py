"""Seccion Entrenamiento: grupos por atributo y su historial.

- Grupos: los 15 atributos entrenables en 3 columnas (fisico/tecnico/mental), cada uno
  con cuantos jugadores lo entrenan. Con Enter se abre la asignacion de ese atributo.
  La cabecera muestra la CAPACIDAD de entreno del club (DT + Centro de entrenamiento +
  staff), que es el techo blando hacia el que se puede desarrollar.
- Historial: el resumen semanal de entrenamiento (de las notificaciones).

Cada jugador entrena UN atributo por semana; se resuelve los jueves (ver
simulation/training.py). Esta pantalla solo lee estado y dispara la asignacion.
"""

from rich.text import Text

from ...domain.player import MENTAL_ATTRS, PHYSICAL_ATTRS, TECHNICAL_ATTRS
from ...simulation import facilities as fac
from ...simulation import notifications as notif
from ...simulation import staff
from ...simulation import training as tr
from ..format import append_section, hint
from ..player_labels import ATTR_LABEL
from .section_screen import SectionScreen

_COLS = [("FISICO", PHYSICAL_ATTRS), ("TECNICO", TECHNICAL_ATTRS), ("MENTAL", MENTAL_ATTRS)]
_COL_W = 26


class TrainingScreen(SectionScreen):
    """Grupos de entrenamiento por atributo e historial."""

    section_key = "E"
    section_title = "Entrenamiento"
    tabs = ("Grupos", "Historial")

    def __init__(self) -> None:
        super().__init__()
        self._row = 0  # 0-4 (fila de atributo)
        self._col = 0  # 0-2 (fisico/tecnico/mental)

    @property
    def _club(self):
        game = self.app.game
        return game.player_club if game else None

    def _selected_attr(self) -> str:
        return _COLS[self._col][1][self._row]

    def render_tab(self, index: int) -> Text:
        if index == 1:
            return self._history_text()
        return self._groups_text()

    def _groups_text(self) -> Text:
        club = self._club
        if club is None:
            return Text("Sin club todavia.", style="white")
        t = Text()
        base = club.coach.skill if club.coach else 40.0
        t.append("ENTRENAMIENTO   ", style="bold green")
        t.append(f"Capacidad {tr.capacity(club):.0f}  ", style="bold white")
        t.append(f"(DT {base:.0f} + Centro {fac.training_capacity_pts(club)} + "
                 f"Staff {staff.training_bonus(club):.0f})\n", style="grey70")
        t.append("-" * 80 + "\n", style="grey50")
        counts = tr.group_counts(club)
        for title, _ in _COLS:
            t.append(title.ljust(_COL_W), style="bold green")
        t.append("\n")
        for r in range(5):
            for c, (_, attrs) in enumerate(_COLS):
                attr = attrs[r]
                cell = f"{ATTR_LABEL[attr]} ({counts.get(attr, 0)})"
                if r == self._row and c == self._col:
                    t.append(("> " + cell).ljust(_COL_W), style="bold black on green")
                else:
                    t.append(("  " + cell).ljust(_COL_W),
                             style="white" if counts.get(attr, 0) else "grey70")
            t.append("\n")
        t.append("\n")
        assigned = sum(counts.values())
        t.append(f"Sin entrenar: {len(club.players) - assigned} de {len(club.players)}\n",
                 style="grey62")
        t.append_text(hint(("flechas", "mover"), ("Enter", "asignar jugadores")))
        return t

    def on_content_key(self, event) -> None:
        if self._active_tab != 0 or self._club is None:
            return
        key = event.key
        if key == "up":
            event.stop(); self._row = (self._row - 1) % 5; self._refresh_content()
        elif key == "down":
            event.stop(); self._row = (self._row + 1) % 5; self._refresh_content()
        elif key == "left":
            event.stop(); self._col = (self._col - 1) % 3; self._refresh_content()
        elif key == "right":
            event.stop(); self._col = (self._col + 1) % 3; self._refresh_content()
        elif key == "enter":
            event.stop()
            from .training_assign_screen import TrainingAssignScreen

            self.app.push_screen(TrainingAssignScreen(
                self.app.game, self._selected_attr(), on_close=self._refresh_content))

    def _history_text(self) -> Text:
        t = Text()
        items = [n for n in notif.all_newest_first(self.app.game)
                 if n.category == notif.TRAINING][:12]
        if not items:
            append_section(t, "HISTORIAL DE ENTRENAMIENTO", [
                ("Todavia no hay entrenamientos registrados.", "grey62"),
                "",
                ("Arma grupos en la pestana Grupos y avanza al jueves.", "grey62"),
            ])
            return t
        t.append("HISTORIAL DE ENTRENAMIENTO\n", style="bold green")
        t.append("-" * 80 + "\n", style="grey50")
        for n in items:
            t.append(f"{n.date.strftime('%d-%m-%Y')}  ", style="grey50")
            t.append(n.message[:66] + "\n", style="grey70")
        return t
