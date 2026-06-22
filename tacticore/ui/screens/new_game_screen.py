"""Pantalla de nuevo juego: pide el nombre del club del jugador.

Al confirmar, guarda el nombre y entra a la Oficina.
"""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, Static

from .base_screen import BaseScreen


class NewGameScreen(BaseScreen):
    """Pide el nombre del club para arrancar la partida."""

    CSS = """
    #viewport {
        align: center middle;
    }
    #box {
        width: 60;
        height: auto;
    }
    #title {
        width: 1fr;
        text-align: center;
        color: green;
        text-style: bold;
    }
    #prompt {
        width: 1fr;
        text-align: center;
        color: white;
        padding: 1 0;
    }
    Input {
        border: ascii green;
    }
    """

    def compose_viewport(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Static("NUEVO JUEGO", id="title")
            yield Static("Nombre de tu club:", id="prompt")
            yield Input(placeholder="Mi Club FC", id="club")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        # Import local para evitar imports circulares.
        from .office_screen import OfficeScreen

        self.app.club_name = event.value.strip() or "Mi Club"
        self.app.switch_screen(OfficeScreen())
