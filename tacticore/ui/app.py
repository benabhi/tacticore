"""Aplicacion principal de Textual.

Arranca en la pantalla de titulo. El flujo es:

    Titulo -> (si no hay mundo) Carga -> Nuevo juego -> Oficina

El estado de la partida (semilla, mundo generado, nombre del club) vive en la
app por ahora; mas adelante se movera a GameState / persistencia.
"""

import random

from textual.app import App

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
        self.world = None
        # Datos del manager (el jugador) y su club (se cargan en "Crea tu club").
        self.manager_name: str | None = None
        self.club_name: str | None = None
        self.club_fans: str | None = None
        self.club_stadium: str | None = None
        self.club_country: str | None = None

    def on_mount(self) -> None:
        self.push_screen(TitleScreen())


def run() -> None:
    """Lanza la aplicacion."""
    TacticoreApp().run()
