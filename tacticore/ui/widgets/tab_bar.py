"""Barra de pestañas (sub-secciones) arriba de una seccion.

Espeja a `NavBar` pero para las sub-secciones de una seccion: muestra las
pestañas con su numero ([1], [2], ...) y resalta la activa. El cambio de pestaña
lo maneja la pantalla (ver SectionScreen): numeros para salto directo o
Tab/Shift+Tab para ciclar.
"""

from rich.text import Text
from textual.widgets import Static


class TabBar(Static):
    """Fila superior con las pestañas de la seccion; la activa resaltada."""

    DEFAULT_CSS = """
    TabBar {
        height: 1;
        color: white;
    }
    """

    def __init__(self, tabs, active: int = 0, **kwargs) -> None:
        super().__init__(**kwargs)
        self._tabs = list(tabs)
        self._active = active

    def on_mount(self) -> None:
        self._render_tabs()

    def set_active(self, index: int) -> None:
        """Cambia la pestaña resaltada."""
        self._active = index
        self._render_tabs()

    def _render_tabs(self) -> None:
        # El numero entre corchetes es el atajo (ASCII), no un color. La activa va
        # resaltada en verde (como la barra inferior); las demas, texto tenue.
        text = Text(no_wrap=True)
        text.append(" ")
        for i, label in enumerate(self._tabs):
            chunk = f"[{i + 1}] {label} " if len(self._tabs) > 1 else f"{label} "
            if i == self._active:
                text.append(chunk, style="bold black on green")
            else:
                text.append(chunk, style="grey70")
            text.append("  ")
        self.update(text)
