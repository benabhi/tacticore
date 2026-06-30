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
    ("L", "Liga"),
]


class NavBar(Static):
    """Barra verde de una fila con las secciones navegables."""

    DEFAULT_CSS = """
    NavBar {
        height: 1;
        background: green;
        color: black;
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
        # Dos verdes nada mas: el fondo de la barra (CSS) y el bloque "on green"
        # del seleccionado (que se ve mas brillante). Los no seleccionados son
        # solo texto negro, sin fondo, asi se ve la barra debajo. El atajo lo
        # indican los corchetes [X] (ASCII), no un color.
        text = Text(no_wrap=True)
        text.append(" ")
        for key, label in SECTIONS:
            chunk = f"[{key}] {label} "
            if key == self._active:
                text.append(chunk, style="bold black on green")
            else:
                text.append(chunk, style="black")
            text.append("  ")
        self.update(text)
