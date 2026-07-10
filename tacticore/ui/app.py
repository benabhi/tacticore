"""Aplicacion principal de Textual.

Arranca en la pantalla de titulo. El flujo de una partida nueva es:

    Titulo -> Carga (genera el mundo) -> Crea tu club -> Club (Oficina)

Si hay una partida guardada, el Titulo ofrece "Continuar" y carga directo al
Club. Todo el estado vive en `self.game` (un `GameState`), que es lo que se
serializa a disco (ver persistence/savegame.py).
"""

import random

from textual.app import App

from ..core.game import GameState
from .screens.title_screen import TitleScreen


class TacticoreApp(App):
    """App raiz del juego."""

    CSS = """
    Screen {
        background: black;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        # Semilla de la partida: reproducible si se conoce. Mas adelante el
        # jugador va a poder elegirla en el menu de nuevo juego.
        self.seed: int = random.Random().randint(1, 999_999)
        # Estado raiz de la partida en curso (None hasta generar/cargar).
        self.game: GameState | None = None

    def on_mount(self) -> None:
        self.push_screen(TitleScreen())


def run() -> None:
    """Lanza la aplicacion."""
    TacticoreApp().run()
