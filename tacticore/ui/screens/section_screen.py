"""Pantalla base de seccion con frame estandar (barra inferior + pestañas).

Cada seccion del juego (Oficina, Club, Jugadores, Liga, Partidos, Entreno,
Finanzas) es una pantalla completa que comparte el mismo marco de 80x25:

    Fila 0 : TITULO ....................................  fecha   caja   (HUD)
    Fila 1 : [1] Pestaña  [2] Pestaña  ...                          (TabBar)
    Fila 2 : ======================================================  (separador)
    ...    : contenido de la pestaña activa
    Fila 24: [O]ficina [C]lub ...                                   (NavBar)

Las subclases declaran `section_key`, `title` y `tabs`, y devuelven el contenido
de cada pestaña en `render_tab(index)`. La navegacion:
- letras -> cambian de SECCION (barra inferior),
- numeros 1..9 / Tab / Shift+Tab -> cambian de PESTAÑA (sub-seccion).

Las pestañas interactivas (ej. la tabla de plantilla) reciben el resto del
teclado en `on_content_key` y re-renderizan su `Text`.
"""

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from ... import config
from ..widgets.nav_bar import NavBar
from ..widgets.tab_bar import TabBar
from ..widgets.top_bar import TopBar
from .base_screen import BaseScreen

# Letra de atajo -> clave de seccion (para la barra inferior).
_SECTION_KEYS = {"o": "O", "c": "C", "j": "J", "l": "L", "p": "P", "e": "E", "f": "F"}


class SectionScreen(BaseScreen):
    """Base de las secciones: frame con HUD, pestañas, contenido y barra inferior."""

    section_key = "O"
    section_title = ""
    tabs: tuple[str, ...] = ("Resumen",)

    CSS = """
    #sep {
        height: 1;
        color: grey;
    }
    #content {
        height: 1fr;
        padding: 1 0 0 0;
        color: white;
    }
    """

    _active_tab = 0

    def compose_viewport(self) -> ComposeResult:
        # Orden: HUD, separador, y la barra de pestañas DEBAJO del separador (solo
        # si hay mas de una). Con una sola pestaña no se dibuja: esa fila queda
        # para el contenido (las pestañas son opcionales).
        with Vertical():
            yield TopBar(self.section_title, id="topbar")
            yield Static("=" * config.SCREEN_WIDTH, id="sep")
            if len(self.tabs) > 1:
                yield TabBar(self.tabs, id="tabbar")
            yield Static(id="content")
            yield NavBar(active=self.section_key)

    def on_mount(self) -> None:
        self._refresh_topbar()
        self._refresh_content()

    # --- Contenido: lo provee la subclase ---
    def render_tab(self, index: int) -> Text:
        """Devuelve el contenido (Text) de la pestaña `index`. Override obligatorio."""
        raise NotImplementedError

    def on_content_key(self, event) -> None:
        """Teclas que no maneja el frame; las usa la pestaña interactiva activa."""

    def content_captures_keys(self) -> bool:
        """Si la pestaña activa quiere TODO el teclado (ej. un buscador abierto).

        Cuando devuelve True, el frame no aplica sus atajos (secciones, pestañas,
        avanzar dia) y le pasa la tecla directo a `on_content_key`.
        """
        return False

    # --- Barra informativa superior (componente TopBar) ---
    def _refresh_topbar(self) -> None:
        self.query_one("#topbar", TopBar).refresh_bar()

    def _refresh_content(self) -> None:
        self.query_one("#content", Static).update(self.render_tab(self._active_tab))

    # --- Navegacion de pestañas ---
    def _set_tab(self, index: int) -> None:
        if index == self._active_tab or not (0 <= index < len(self.tabs)):
            return
        self._active_tab = index
        if len(self.tabs) > 1:  # la barra solo existe con mas de una pestaña
            self.query_one("#tabbar", TabBar).set_active(index)
        self._refresh_content()

    def _cycle_tab(self, delta: int) -> None:
        if len(self.tabs) > 1:
            self._set_tab((self._active_tab + delta) % len(self.tabs))

    # --- Game loop: avanzar el tiempo ---
    def _advance_day(self) -> None:
        game = getattr(self.app, "game", None)
        if game is None:
            return
        game.calendar.advance(1)
        # Al avanzar cambia la fecha (y mas adelante se disparan eventos): se
        # refresca el HUD y el contenido, que puede depender de la fecha.
        self._refresh_topbar()
        self._refresh_content()

    # --- Teclado del frame ---
    # OJO: no sobrescribir on_key en las subclases. Textual invoca el handler de
    # CADA clase de la jerarquia (MRO), asi que un on_key en la subclase se
    # sumaria a este y las teclas se procesarian dos veces. Las subclases usan
    # on_content_key (y content_captures_keys) en su lugar.
    def on_key(self, event) -> None:
        if self.content_captures_keys():
            self.on_content_key(event)
            return
        key = event.key
        if key == "space":
            event.stop()
            self._advance_day()
        elif len(key) == 1 and key.isdigit() and key != "0":
            event.stop()
            self._set_tab(int(key) - 1)
        elif key == "tab":
            event.stop()
            self._cycle_tab(1)
        elif key == "shift+tab":
            event.stop()
            self._cycle_tab(-1)
        elif key in _SECTION_KEYS:
            event.stop()
            self.action_goto(_SECTION_KEYS[key])
        else:
            self.on_content_key(event)

    def action_goto(self, key: str) -> None:
        """Salta a otra seccion (si no es la actual)."""
        if key == self.section_key:
            return
        # Import local para evitar imports circulares entre secciones.
        from .club_screen import ClubScreen
        from .finance_screen import FinanceScreen
        from .league_screen import LeagueScreen
        from .matches_screen import MatchesScreen
        from .office_screen import OfficeScreen
        from .players_screen import PlayersScreen
        from .training_screen import TrainingScreen

        screens = {
            "O": OfficeScreen,
            "C": ClubScreen,
            "J": PlayersScreen,
            "L": LeagueScreen,
            "P": MatchesScreen,
            "E": TrainingScreen,
            "F": FinanceScreen,
        }
        self.app.switch_screen(screens[key]())
