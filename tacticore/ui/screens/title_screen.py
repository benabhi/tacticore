"""Pantalla de titulo: ASCII-art del nombre + 'Presiona ENTER' parpadeante.

Estilo arcade viejo. Al presionar Enter: si todavia no hay mundo generado, va a
la pantalla de carga; si ya existe, va directo a la Oficina.
"""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from ..art import render_banner
from .base_screen import BaseScreen

_PROMPT = "Presiona <ENTER> para comenzar"


class TitleScreen(BaseScreen):
    """Portada del juego."""

    BINDINGS = [("enter", "start", "Comenzar")]

    CSS = """
    #viewport {
        align: center middle;
    }
    #box {
        width: 60;
        height: auto;
    }
    #banner {
        width: 1fr;
        text-align: center;
        color: green;
        text-style: bold;
    }
    #prompt {
        width: 1fr;
        text-align: center;
        color: yellow;
        padding-top: 2;
    }
    """

    def compose_viewport(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Static("\n".join(render_banner("TACTICORE")), id="banner")
            yield Static(_PROMPT, id="prompt")

    def on_mount(self) -> None:
        self._blink_on = True
        # Parpadeo del texto cada medio segundo.
        self.set_interval(0.5, self._toggle_blink)

    def _toggle_blink(self) -> None:
        self._blink_on = not self._blink_on
        self.query_one("#prompt", Static).update(_PROMPT if self._blink_on else "")

    def action_start(self) -> None:
        # Import local para evitar imports circulares.
        if self.app.world is None:
            from .loading_screen import LoadingScreen

            self.app.switch_screen(LoadingScreen())
        else:
            from .office_screen import OfficeScreen

            self.app.switch_screen(OfficeScreen())
