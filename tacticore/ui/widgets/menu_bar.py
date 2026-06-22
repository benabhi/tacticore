"""Barra de menu inferior (HUD).

Por ahora es un placeholder; mas adelante mostrara las acciones disponibles
(continuar, plantilla, tabla, guardar, etc.).
"""

from textual.widgets import Static


class MenuBar(Static):
    """Barra negra de una fila al pie de la pantalla."""

    DEFAULT_CSS = """
    MenuBar {
        height: 1;
        background: black;
        color: white;
        content-align: left middle;
    }
    """
