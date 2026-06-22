"""Pantalla base: encierra el contenido en un viewport fijo de 80x25.

Asi TODO el juego ocupa siempre un area de 80 columnas x 25 filas, anclada en la
esquina superior izquierda de la terminal (posicion natural), sin importar cuan
grande sea la ventana real (directiva 1). Si la terminal es mas grande, sobra
espacio a la derecha y abajo; se ajusta agrandando la fuente. Las subclases
definen su contenido en `compose_viewport()`; ese contenido vive dentro del
`#viewport` (de 80x25), no de la terminal entera.
"""

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen

from ... import config


class BaseScreen(Screen):
    """Base de todas las pantallas: aporta el viewport fijo de 80x25."""

    DEFAULT_CSS = f"""
    BaseScreen {{
        background: black;
    }}
    #viewport {{
        width: {config.SCREEN_WIDTH};
        height: {config.SCREEN_HEIGHT};
    }}
    """

    def compose(self) -> ComposeResult:
        with Container(id="viewport"):
            yield from self.compose_viewport()

    def compose_viewport(self) -> ComposeResult:
        """Las subclases devuelven aca los widgets que van dentro del viewport."""
        raise NotImplementedError
