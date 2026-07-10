"""Barra informativa superior (una fila, con fondo de color).

Comun a todas las secciones. De izquierda a derecha:

- la "pestaña" del nombre de la pantalla, en una columna negra (se ve como una
  solapa sobre el fondo azul);
- el control de avanzar dia ([Espacio]);
- la SEMANA: los 7 dias (Lun..Dom) con el dia actual resaltado, y la fecha de hoy.
  Asi se ve de un vistazo en que dia de la semana estamos (el detalle de los
  eventos vive en el calendario de Club > Oficina);
- un indicador de notificaciones sin leer: el numero con fondo amarillo.

No repite datos que ya viven en sus pantallas (caja, proximo partido): la barra es
para el pulso del tiempo y las novedades. El fondo azul se pinta con spans
(`on BAR_BG`) sobre toda la fila MENOS la pestaña del nombre (que va sin fondo).
"""

from rich.text import Text
from textual.widgets import Static

from ... import config
from ...simulation import notifications as notif
from ..palette import ACCENT, BAR_BG

_TAB_W = 14  # ancho de la pestaña del nombre (entra " ENTRENAMIENTO", el mas largo)
_BG = f"on {BAR_BG}"   # sufijo de estilo para pintar el fondo de la barra
_DOW = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]  # 0=lunes .. 6=domingo
_CONTROL = " [Espacio] avanzar"  # control de avanzar dia (la tecla va en acento)


class TopBar(Static):
    """Fila superior: pestaña + avanzar dia + hoy/siguiente + notificaciones."""

    DEFAULT_CSS = """
    TopBar {
        height: 1;
    }
    """

    def __init__(self, title: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self._title = title

    def refresh_bar(self) -> None:
        """Re-renderiza la barra (cambia la fecha, el evento o las notificaciones)."""
        self.refresh()

    def render(self) -> Text:
        t = Text(no_wrap=True)
        # Pestaña: nombre de pantalla en verde, SIN fondo -> negro de la terminal.
        tab = (" " + self._title.upper()).ljust(_TAB_W)[:_TAB_W]
        t.append(tab, style="bold green")

        game = getattr(self.app, "game", None)
        if game is None:
            t.append(" " * (config.SCREEN_WIDTH - _TAB_W), style=_BG)
            return t

        # Control de avanzar dia (la tecla resaltada), pegado a la pestaña.
        t.append(" [", style=f"grey62 {_BG}")
        t.append("Espacio", style=f"bold {ACCENT} {_BG}")
        t.append("] avanzar", style=f"white {_BG}")

        # Cluster derecho: la SEMANA (Lun..Dom, con hoy resaltado) + la fecha de hoy +
        # el contador de notificaciones sin leer.
        cur = game.calendar.current_date
        fecha = cur.strftime("%d-%m-%Y")
        unread = notif.unread_count(game)
        badge = f" {unread} " if unread > 0 else ""

        # Ancho del cluster: 7 dias de 3 chars + 6 separadores (1) + "  " + fecha (10)
        # + (1 + badge). Se rellena el medio con el fondo de la barra.
        week_len = 7 * 3 + 6
        right_len = week_len + 2 + len(fecha) + (1 + len(badge) if badge else 0)
        used = _TAB_W + len(_CONTROL)
        t.append(" " * max(1, config.SCREEN_WIDTH - used - right_len), style=_BG)
        for i, name in enumerate(_DOW):
            if i == cur.weekday():
                t.append(name, style=f"bold black on {ACCENT}")   # hoy: resaltado
            else:
                t.append(name, style=f"grey62 {_BG}")
            if i < 6:
                t.append(" ", style=_BG)
        t.append("  ", style=_BG)
        t.append(fecha, style=f"white {_BG}")
        if badge:
            t.append(" ", style=_BG)
            t.append(badge, style=f"bold black on {ACCENT}")
        return t
