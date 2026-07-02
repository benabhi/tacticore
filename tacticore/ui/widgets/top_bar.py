"""Barra informativa superior (una fila, con fondo de color).

Comun a todas las secciones: a la izquierda, el nombre de la pantalla en una
"columna" negra (se ve como una pestaña sobre el fondo azul); pegado a ella, el
control de avanzar dia ([Espacio] > dia); y a la derecha, datos del club (fecha,
caja y el proximo partido).

El fondo azul se pinta con spans (`on BAR_BG`) sobre toda la fila MENOS la columna
del nombre: esa pestaña va SIN fondo, asi muestra el negro real de la terminal (y
no un negro forzado que se veria distinto).
"""

from rich.text import Text
from textual.widgets import Static

from ... import config
from ..format import money
from ..palette import ACCENT, BAR_BG

_TAB_W = 11  # ancho de la pestaña del nombre (entra "JUGADORES", el mas largo)
_ADVANCE = "] Avanzar dia"  # texto del control de avanzar dia (tras "[Espacio")
_BG = f"on {BAR_BG}"   # sufijo de estilo para pintar el fondo de la barra


class TopBar(Static):
    """Fila superior con la pestaña del nombre + avanzar dia + datos del club."""

    DEFAULT_CSS = """
    TopBar {
        height: 1;
    }
    """

    def __init__(self, title: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self._title = title

    def refresh_bar(self) -> None:
        """Re-renderiza la barra (ej. al avanzar el dia cambia la fecha)."""
        self.refresh()

    def _next_match_text(self, game, club) -> str:
        """'Prox J{jornada} {dd-mm}' del proximo partido del club (o '')."""
        league = game.player_league
        if league is None or club is None:
            return ""
        for m in sorted(league.matches, key=lambda m: m.matchday):
            if not m.played and (m.home is club or m.away is club):
                when = m.match_date.strftime("%d-%m") if m.match_date else ""
                return f"Prox J{m.matchday} {when}".rstrip()
        return ""

    def render(self) -> Text:
        t = Text(no_wrap=True)
        # Pestaña: nombre de pantalla en verde, SIN fondo -> negro de la terminal.
        tab = (" " + self._title.upper()).ljust(_TAB_W)[:_TAB_W]
        t.append(tab, style="bold green")

        game = getattr(self.app, "game", None)
        club = game.player_club if game else None
        if club is None:
            t.append(" " * (config.SCREEN_WIDTH - _TAB_W), style=_BG)
            return t

        # Avanzar dia, pegado a la pestaña (izquierda). Todo con el fondo azul.
        t.append(" [", style=f"grey62 {_BG}")
        t.append("Espacio", style=f"bold {ACCENT} {_BG}")
        t.append(_ADVANCE, style=f"white {_BG}")

        # Cluster derecho: fecha, proximo partido y, al final (mas a la derecha),
        # la caja del club.
        date = game.calendar.current_date.strftime("%d-%m-%Y")
        cash = money(club.capital)
        nxt = self._next_match_text(game, club)
        right = [(date, f"grey70 {_BG}")]
        if nxt:
            right.append((nxt, f"grey70 {_BG}"))
        right.append((cash, f"bold white {_BG}"))
        right_len = sum(len(txt) for txt, _ in right) + 3 * (len(right) - 1)

        used = _TAB_W + len(" [") + len("Espacio") + len(_ADVANCE)
        pad = config.SCREEN_WIDTH - used - right_len - 1  # -1: margen al borde
        t.append(" " * max(1, pad), style=_BG)
        for i, (txt, style) in enumerate(right):
            if i:
                t.append("   ", style=_BG)
            t.append(txt, style=style)
        t.append(" ", style=_BG)
        return t
