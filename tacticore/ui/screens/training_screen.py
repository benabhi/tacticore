"""Seccion Entrenamiento: grupos por atributo (arriba) + informe semanal (abajo).

Una sola vista (sin pestanas): en la mitad de arriba, los 15 atributos entrenables
en 3 columnas (fisico/tecnico/mental) con cuantos jugadores entrenan cada uno; con
las flechas ARRIBA/ABAJO se elige el atributo y con Enter se abre la asignacion. La
cabecera muestra la CAPACIDAD de entreno (DT + Centro + staff), el techo blando.

En la mitad de abajo, el INFORME de entrenamiento de cada semana (de las
notificaciones de categoria entrenamiento): las flechas IZQUIERDA/DERECHA se mueven
entre los informes (mas nuevo <-> mas viejo) para ver en detalle que mejoro cada uno.

Cada jugador entrena UN atributo por semana; se resuelve los jueves (ver
simulation/training.py). Esta pantalla solo lee estado y dispara la asignacion.
"""

from rich.text import Text

from ...domain.player import MENTAL_ATTRS, PHYSICAL_ATTRS, TECHNICAL_ATTRS
from ...simulation import facilities as fac
from ...simulation import notifications as notif
from ...simulation import staff
from ...simulation import training as tr
from ..format import hint, training_report_lines
from ..player_labels import ATTR_LABEL
from .section_screen import SectionScreen

_COLS = [("FISICO", PHYSICAL_ATTRS), ("TECNICO", TECHNICAL_ATTRS), ("MENTAL", MENTAL_ATTRS)]
_COL_W = 26
_CONTENT_ROWS = 20  # alto util del contenido (ancla la ayuda al fondo, con un espacio)


class TrainingScreen(SectionScreen):
    """Grupos de entrenamiento por atributo + informe semanal, en una vista."""

    section_key = "E"
    section_title = "Entrenamiento"
    tabs = ("Entrenamiento",)   # una sola vista: no se dibuja barra de pestanas

    def __init__(self) -> None:
        super().__init__()
        self._sel = 0        # atributo elegido (0-14, orden por columnas)
        self._report = 0     # informe elegido (0 = el mas reciente)

    @property
    def _club(self):
        game = self.app.game
        return game.player_club if game else None

    def _selected_attr(self) -> str:
        col, row = divmod(self._sel, 5)
        return _COLS[col][1][row]

    def _reports(self) -> list:
        game = self.app.game
        return [n for n in notif.all_newest_first(game)
                if n.category == notif.TRAINING] if game else []

    def render_tab(self, index: int) -> Text:
        club = self._club
        if club is None:
            return Text("Sin club todavia.", style="white")
        lines = self._group_lines(club)
        lines.append(Text("-" * 80, style="grey50"))
        # El informe llena desde aca hasta el fondo (la ayuda queda a un espacio del menu).
        avail = (_CONTENT_ROWS - 1) - len(lines) - 1   # filas para el cuerpo del informe
        lines += self._report_lines(avail)

        t = Text()
        for ln in lines[:_CONTENT_ROWS - 1]:
            t.append_text(ln); t.append("\n")
        for _ in range(_CONTENT_ROWS - 1 - len(lines)):
            t.append("\n")                       # empuja la ayuda al fondo (con un espacio)
        t.append_text(hint(("^v", "atributo"), ("Enter", "asignar"),
                           ("<>", "informe")))
        return t

    def _group_lines(self, club) -> list:
        base = club.coach.skill if club.coach else 40.0
        head = Text()
        head.append("ENTRENAMIENTO   ", style="bold green")
        head.append(f"Capacidad {tr.capacity(club):.0f}  ", style="bold white")
        head.append(f"(DT {base:.0f} + Centro {fac.training_capacity_pts(club)} + "
                    f"Staff {staff.training_bonus(club):.0f})", style="grey70")
        lines = [head, Text("-" * 80, style="grey50")]
        titles = Text()
        for title, _ in _COLS:
            titles.append(title.ljust(_COL_W), style="bold green")
        lines.append(titles)
        counts = tr.group_counts(club)
        for r in range(5):
            row = Text()
            for c, (_, attrs) in enumerate(_COLS):
                attr = attrs[r]
                cell = f"{ATTR_LABEL[attr]} ({counts.get(attr, 0)})"
                if c * 5 + r == self._sel:
                    row.append(("> " + cell).ljust(_COL_W), style="bold black on green")
                else:
                    row.append(("  " + cell).ljust(_COL_W),
                               style="white" if counts.get(attr, 0) else "grey70")
            lines.append(row)
        assigned = sum(counts.values())
        lines.append(Text(f"Sin entrenar: {len(club.players) - assigned} de "
                          f"{len(club.players)} jugadores", style="grey62"))
        return lines

    def _report_lines(self, avail: int) -> list:
        reports = self._reports()
        if not reports:
            return [Text("INFORME DE ENTRENAMIENTO", style="bold green"),
                    Text("Todavia no hubo entrenamientos. Arma grupos y avanza al jueves.",
                         style="grey62")]
        self._report = max(0, min(len(reports) - 1, self._report))
        n = reports[self._report]
        head = Text()
        head.append("INFORME DE ENTRENAMIENTO", style="bold green")
        head.append(f"   {n.date.strftime('%d-%m-%Y')}   "
                    f"({self._report + 1}/{len(reports)})", style="grey62")
        # El detalle en 2 columnas legibles (resumen + mejoras, ganancia en verde).
        return [head] + training_report_lines(n.message, avail)

    def on_content_key(self, event) -> None:
        if self._club is None:
            return
        key = event.key
        if key == "up":
            event.stop(); self._sel = (self._sel - 1) % 15; self._refresh_content()
        elif key == "down":
            event.stop(); self._sel = (self._sel + 1) % 15; self._refresh_content()
        elif key == "left":                      # informe mas nuevo
            event.stop(); self._report = max(0, self._report - 1); self._refresh_content()
        elif key == "right":                     # informe mas viejo
            event.stop()
            self._report = min(max(0, len(self._reports()) - 1), self._report + 1)
            self._refresh_content()
        elif key == "enter":
            event.stop()
            from .training_assign_screen import TrainingAssignScreen

            self.app.push_screen(TrainingAssignScreen(
                self.app.game, self._selected_attr(), on_close=self._refresh_content))
