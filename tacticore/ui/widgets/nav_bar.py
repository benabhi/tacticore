"""Barra de navegacion inferior (estilo UI vieja: [O]ficina  [C]lub ...).

Muestra las secciones del juego con su tecla de acceso entre corchetes; la
seccion activa queda resaltada. El cambio de seccion lo maneja la pantalla
(ver SectionScreen).
"""

from rich.text import Text
from textual.widgets import Static

# Secciones: (tecla, etiqueta). El orden es el de la barra.
SECTIONS: list[tuple[str, str]] = [
    ("O", "Oficina"),
    ("C", "Club"),
    ("J", "Jugadores"),
]


class NavBar(Static):
    """Barra negra de una fila con las secciones navegables."""

    DEFAULT_CSS = """
    NavBar {
        height: 1;
        background: black;
        color: white;
    }
    """

    def __init__(self, active: str = "O", **kwargs) -> None:
        super().__init__(**kwargs)
        self._active = active

    def on_mount(self) -> None:
        self._render_nav()

    def set_active(self, key: str) -> None:
        """Cambia la seccion resaltada."""
        self._active = key
        self._render_nav()

    def _render_nav(self) -> None:
        text = Text(no_wrap=True)
        text.append(" ")
        for key, label in SECTIONS:
            if key == self._active:
                text.append(f"[{key}]{label}", style="bold black on white")
            else:
                text.append(f"[{key}]{label}", style="white")
            text.append("  ")
        self.update(text)
