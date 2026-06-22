"""Pantalla de nuevo juego: pide el nombre del club del jugador.

Al confirmar, guarda el nombre y entra a la Oficina.
"""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Input, Static


class NewGameScreen(Screen):
    """Pide el nombre del club para arrancar la partida."""

    CSS = """
    NewGameScreen {
        align: center middle;
        background: black;
    }
    #box {
        width: 60;
        height: auto;
    }
    #title {
        text-align: center;
        color: green;
        text-style: bold;
    }
    #prompt {
        text-align: center;
        color: white;
        padding: 1 0;
    }
    Input {
        border: ascii green;
    }
    """

    def compose(self) -> ComposeResult:
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
