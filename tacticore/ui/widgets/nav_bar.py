"""Barra de navegacion inferior (estilo UI vieja: [O]ficina  [C]lub ...).

Muestra las secciones del juego con su tecla de acceso entre corchetes; la
seccion activa queda resaltada. El cambio de seccion lo maneja la pantalla
(ver SectionScreen).
"""

from rich.text import Text
from textual.widgets import Static

from ..palette import ACCENT

# Secciones: (tecla, etiqueta). El orden es el de la barra.
SECTIONS: list[tuple[str, str]] = [
    ("O", "Oficina"),
    ("C", "Club"),
    ("J", "Jugadores"),
    ("P", "Partidos"),
    ("E", "Entreno"),
    ("F", "Finanzas"),
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
        # indican los corchetes [X] (ASCII), no un color. Separadores de 1 espacio
        # para que las 7 secciones entren en 80 columnas.
        text = Text(no_wrap=True)
        text.append(" ")
        for i, (key, label) in enumerate(SECTIONS):
            if key == self._active:
                # Seccion activa: bloque negro sobre verde brillante (ya se destaca;
                # no le ponemos acento para que no quede tenue sobre el fondo claro).
                text.append(f"[{key}]{label}", style="bold black on green")
            else:
                # La letra del atajo va con el color de acento (resalta la tecla);
                # los corchetes y la etiqueta, negros sobre el verde de la barra.
                text.append("[", style="black")
                text.append(key, style=f"bold {ACCENT}")
                text.append("]" + label, style="black")
            if i < len(SECTIONS) - 1:
                text.append(" ")
        self.update(text)
