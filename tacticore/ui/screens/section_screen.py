"""Pantalla base de seccion (menus full-screen estilo ADOM).

Cada seccion del juego (Oficina, Club, Jugadores) es una pantalla completa que
comparte la barra de navegacion inferior y las teclas para saltar entre
secciones. Las subclases solo definen su contenido en `content()`.
"""

from collections.abc import Iterator

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widget import Widget

from ..widgets.nav_bar import NavBar


class SectionScreen(Screen):
    """Base de las pantallas de seccion. La subclase fija `section_key`."""

    section_key = "O"

    BINDINGS = [
        ("o", "goto('O')", "Oficina"),
        ("c", "goto('C')", "Club"),
        ("j", "goto('J')", "Jugadores"),
    ]

    CSS = """
    SectionScreen {
        background: black;
    }
    #content {
        height: 1fr;
        padding: 1 2;
        color: white;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="content"):
            yield from self.content()
        yield NavBar(active=self.section_key)

    def content(self) -> Iterator[Widget]:
        """Las subclases devuelven aca los widgets de su contenido."""
        raise NotImplementedError

    def action_goto(self, key: str) -> None:
        """Salta a otra seccion (si no es la actual)."""
        if key == self.section_key:
            return
        # Import local para evitar imports circulares entre secciones.
        from .club_screen import ClubScreen
        from .office_screen import OfficeScreen
        from .players_screen import PlayersScreen

        screens = {"O": OfficeScreen, "C": ClubScreen, "J": PlayersScreen}
        self.app.switch_screen(screens[key]())
