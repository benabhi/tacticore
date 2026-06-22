"""Aplicacion principal de Textual.

Compone la pantalla de juego: la cancha ocupa el area superior y la barra de
menu, la fila inferior. Todo dentro de un contenedor fijo de 80x25.
"""

from textual.app import App, ComposeResult
from textual.containers import Vertical

from ..config import SCREEN_HEIGHT, SCREEN_WIDTH
from .widgets.field import GRASS_DARK, SoccerField
from .widgets.menu_bar import MenuBar


class TacticoreApp(App):
    """App raiz del juego."""

    # El fondo de la cancha usa el verde oscuro del cesped, asi la columna/fila
    # sobrante (la cancha es impar) se mezcla con las franjas.
    CSS = f"""
    Screen {{
        background: black;
    }}
    #game {{
        width: {SCREEN_WIDTH};
        height: {SCREEN_HEIGHT};
    }}
    SoccerField {{
        height: 1fr;
        background: {GRASS_DARK};
    }}
    """

    def compose(self) -> ComposeResult:
        # Contenedor fijo de 80x25: cancha (resto) + barra de menu (1 fila).
        with Vertical(id="game"):
            yield SoccerField()
            yield MenuBar(" Tacticore ")


def run() -> None:
    """Lanza la aplicacion."""
    TacticoreApp().run()
