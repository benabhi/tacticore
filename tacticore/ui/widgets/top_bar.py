"""Barra informativa superior (una fila, con fondo de color).

Comun a todas las secciones. De izquierda a derecha:

- la "pestaña" del nombre de la pantalla, en una columna negra (se ve como una
  solapa sobre el fondo azul);
- el control de avanzar dia ([Espacio]);
- el dia de HOY con su evento (resaltado), una flecha, y el dia SIGUIENTE con su
  fecha entera y su evento (en gris). La flecha `->` marca la progresion "hoy lleva
  a manana"; los "dias" son lunes/martes/..., el evento es lo que se procesa ese dia;
- un indicador de notificaciones sin leer: el numero con fondo amarillo.

No repite datos que ya viven en sus pantallas (caja, proximo partido): la barra es
para el pulso del tiempo y las novedades. El fondo azul se pinta con spans
(`on BAR_BG`) sobre toda la fila MENOS la pestaña del nombre (que va sin fondo).
"""

from datetime import timedelta

from rich.text import Text
from textual.widgets import Static

from ... import config
from ...simulation import notifications as notif
from ...simulation.daily import day_event_short
from ..palette import ACCENT, BAR_BG

_TAB_W = 11  # ancho de la pestaña del nombre (entra "JUGADORES", el mas largo)
_BG = f"on {BAR_BG}"   # sufijo de estilo para pintar el fondo de la barra
_DOW = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]  # 0=lunes .. 6=domingo
_CONTROL = " [Espacio] avanzar"  # control de avanzar dia (la tecla va en acento)
_ARROW = " -> "  # separador HOY -> siguiente (4 chars: entra en 80 columnas)


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

        # Cluster derecho: HOY (dia + evento, resaltado) -> siguiente (dia + fecha +
        # evento, en gris) y el contador de notificaciones sin leer. La palabra "Sig"
        # se omite: la flecha ya indica que es el dia que viene.
        cur = game.calendar.current_date
        nxt = cur + timedelta(days=1)
        hoy = f"Hoy {_DOW[cur.weekday()]} {day_event_short(cur)}"
        sig = (f"{_DOW[nxt.weekday()]} {nxt.strftime('%d-%m-%Y')} "
               f"{day_event_short(nxt)}")
        unread = notif.unread_count(game)
        badge = f" {unread} " if unread > 0 else ""

        # El cluster derecho termina justo en la ultima columna (el badge ya trae
        # su propio espacio final). Se rellena el medio con el fondo de la barra.
        # El separador es " -> " (4): con " -> " entra hasta el peor caso de eventos.
        right_len = len(hoy) + len(_ARROW) + len(sig) + (2 + len(badge) if badge else 0)
        used = _TAB_W + len(_CONTROL)
        pad = config.SCREEN_WIDTH - used - right_len
        t.append(" " * max(1, pad), style=_BG)
        t.append(hoy, style=f"bold white {_BG}")          # hoy: resaltado
        t.append(_ARROW, style=f"grey50 {_BG}")           # flecha de progresion
        t.append(sig, style=f"grey62 {_BG}")              # siguiente: tenue
        if badge:
            t.append("  ", style=_BG)
            t.append(badge, style=f"bold black on {ACCENT}")
        return t
