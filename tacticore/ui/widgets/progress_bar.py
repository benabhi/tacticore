"""Widget de barra de progreso (ASCII + colores ANSI).

Reutilizable en cualquier pantalla que necesite mostrar avance: generacion del
mundo, simular jornada, cargar partida, etc. Dibuja algo como:

    [#############---------------]  46%
"""

from rich.text import Text
from textual.widgets import Static

CH_FILLED = "#"
CH_EMPTY = "-"


def bar_text(done: int, total: int, width: int) -> str:
    """Arma la barra como string ASCII puro (sin color). Util para tests."""
    total = max(1, total)
    frac = max(0.0, min(1.0, done / total))
    filled = round(frac * width)
    pct = round(frac * 100)
    return f"[{CH_FILLED * filled}{CH_EMPTY * (width - filled)}] {pct:3d}%"


class ProgressBar(Static):
    """Barra de progreso de una fila."""

    DEFAULT_CSS = """
    ProgressBar {
        height: 1;
        content-align: center middle;
        color: white;
    }
    """

    def __init__(self, width: int = 50, **kwargs) -> None:
        super().__init__(**kwargs)
        self._bar_width = width
        self._done = 0
        self._total = 1

    def on_mount(self) -> None:
        self._refresh_bar()

    def update_progress(self, done: int, total: int) -> None:
        """Actualiza el avance y redibuja la barra."""
        self._done = done
        self._total = max(1, total)
        self._refresh_bar()

    def _refresh_bar(self) -> None:
        total = self._total
        frac = max(0.0, min(1.0, self._done / total))
        filled = round(frac * self._bar_width)
        pct = round(frac * 100)
        # La parte llena en verde brillante; la vacia en gris; el resto blanco.
        text = Text(no_wrap=True)
        text.append("[", style="white")
        text.append(CH_FILLED * filled, style="bold bright_green")
        text.append(CH_EMPTY * (self._bar_width - filled), style="bright_black")
        text.append("]", style="white")
        text.append(f" {pct:3d}%", style="white")
        self.update(text)
