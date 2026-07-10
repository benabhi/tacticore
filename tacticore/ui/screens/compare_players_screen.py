"""Comparacion "versus" de dos jugadores, atributo por atributo, en 80x25.

Se abre desde la tabla de plantilla: se marca un jugador (A) con 'm' y se elige
un segundo (B) con Enter. Cada atributo se muestra con el valor de A y de B a los
lados y una barra divergente al centro que apunta al que gana, proporcional a la
diferencia. El valor mas alto va en VERDE y el mas bajo en ROJO (empate en gris).

Teclas: Esc/Enter volver; 's' intercambia que jugador va de cada lado.
"""

from datetime import date

from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Static

from ...domain.player import ALL_ATTRS
from ..format import hint
from ..player_labels import ATTR_GROUPS, ATTR_LABEL, FOOT_SHORT
from .base_screen import BaseScreen

_W = 76        # ancho util dentro del viewport
_HALF = 38     # media pantalla (para la cabecera a dos columnas)
_BAR_HALF = 10  # semiancho de la barra divergente (ancho total 2*_BAR_HALF+1)


def _cmp_style(mine: float, other: float) -> str:
    """Color de un valor segun la comparacion: verde si es mayor, rojo si menor."""
    if mine > other:
        return "bold green"
    if mine < other:
        return "red"
    return "grey62"


def _diverge_bar(a: float, b: float, half: int = _BAR_HALF) -> str:
    """Barra divergente ASCII: '|' al centro y '#' hacia el que tiene mas.

    La magnitud (cuantos '#') es proporcional a |a-b|, con tope en `half`: una
    diferencia de ~16 puntos llena media barra. Solo caracteres ASCII."""
    width = 2 * half + 1
    cells = [" "] * width
    cells[half] = "|"
    m = min(half, round(abs(a - b) * (half / 16)))
    if a > b:
        for i in range(half - m, half):
            cells[i] = "#"
    elif b > a:
        for i in range(half + 1, half + 1 + m):
            cells[i] = "#"
    return "".join(cells)


def _tally(pa, pb) -> tuple[int, int, int]:
    """(atributos en que gana A, en que gana B, empates) sobre los 15 atributos."""
    wins_a = sum(1 for at in ALL_ATTRS if getattr(pa, at) > getattr(pb, at))
    wins_b = sum(1 for at in ALL_ATTRS if getattr(pa, at) < getattr(pb, at))
    return wins_a, wins_b, len(ALL_ATTRS) - wins_a - wins_b


class ComparePlayersScreen(BaseScreen):
    """Enfrenta dos jugadores atributo por atributo (vista 'versus')."""

    BINDINGS = [
        ("escape", "back", "Volver"),
        ("backspace", "back", "Volver"),
        ("enter", "back", "Volver"),
        ("s", "swap", "Intercambiar"),
    ]

    CSS = """
    #viewport { align: center top; }
    #card {
        width: 76;
        height: auto;
        margin-top: 1;
    }
    #hint {
        dock: bottom;
        width: 76;
        text-align: center;
        color: $text-muted;
    }
    """

    def __init__(self, player_a, player_b, today: date, on_close=None) -> None:
        super().__init__()
        self._a = player_a
        self._b = player_b
        self._today = today
        self._on_close = on_close

    def compose_viewport(self) -> ComposeResult:
        yield Static(self._card_text(), id="card")
        yield Static(
            hint(("Esc", "volver"), ("s", "intercambiar A/B"), sep="   "),
            id="hint",
        )

    def _refresh(self) -> None:
        self.query_one("#card", Static).update(self._card_text())

    # --- Contenido ---
    def _card_text(self) -> Text:
        a, b = self._a, self._b
        t = Text()
        # Cabecera a dos columnas: nombre e identidad de cada lado.
        self._header(t, a, b)
        t.append("-" * _W + "\n", style="grey50")
        # Franja resumen (numeros clave) en una sola fila.
        self._summary(t, a, b)
        # Atributos, agrupados y apilados (cada fila usa el ancho completo).
        for title, attrs in ATTR_GROUPS:
            t.append(title + "\n", style="bold green")
            for attr in attrs:
                self._versus_row(t, ATTR_LABEL[attr],
                                 getattr(a, attr), getattr(b, attr))
        # Recuento final.
        wa, wb, ties = _tally(a, b)
        t.append(f"{a.last_name:.14} supera en {wa}", style="bold white")
        t.append("   -   ", style="grey50")
        t.append(f"{b.last_name:.14} en {wb}", style="bold white")
        t.append("   -   ", style="grey50")
        t.append(f"{ties} empate(s)", style="grey62")
        return t

    def _header(self, t: Text, a, b) -> None:
        left = f"{a.full_name}  (A)"
        right = f"{b.full_name}  (B)"
        t.append(left[:_HALF].ljust(_HALF), style="bold white")
        t.append(right[:_HALF] + "\n", style="bold white")
        t.append(self._meta(a)[:_HALF].ljust(_HALF), style="grey70")
        t.append(self._meta(b)[:_HALF] + "\n", style="grey70")

    def _meta(self, p) -> str:
        dorsal = p.shirt_number or "-"
        return (f"{p.position.value}  #{dorsal}  {p.age_on(self._today)}a  "
                f"{p.nationality}  {FOOT_SHORT[p.foot]}")

    def _summary(self, t: Text, a, b) -> None:
        # (etiqueta, valor A, valor B, formato)
        items = [
            ("OVR", a.overall, b.overall, "{:.1f}"),
            ("POT", a.potential, b.potential, "{:.1f}"),
            ("FOR", a.form, b.form, "{:.1f}"),
            ("FIT", a.fitness, b.fitness, "{:.0f}"),
        ]
        t.append("  ")
        for label, av, bv, fmt in items:
            t.append(f"{label} ", style="bold green")
            t.append(fmt.format(av), style=_cmp_style(av, bv))
            t.append("|", style="grey50")
            t.append(fmt.format(bv), style=_cmp_style(bv, av))
            t.append("   ")
        t.append("\n")

    def _versus_row(self, t: Text, label: str, a: float, b: float) -> None:
        t.append("  ")
        t.append(f"{label:<12.12}", style="grey70")
        t.append(" ")
        t.append(f"{a:>5.1f}", style=_cmp_style(a, b))
        t.append(" ")
        t.append(_diverge_bar(a, b), style="green" if a != b else "grey42")
        t.append(" ")
        t.append(f"{b:<5.1f}", style=_cmp_style(b, a))
        t.append(" ")
        # Etiqueta del ganador + diferencia.
        if a > b:
            t.append(f"A +{a - b:.1f}", style="green")
        elif b > a:
            t.append(f"B +{b - a:.1f}", style="green")
        else:
            t.append("=", style="grey42")
        t.append("\n")

    # --- Navegacion ---
    def action_swap(self) -> None:
        self._a, self._b = self._b, self._a
        self._refresh()

    def action_back(self) -> None:
        if self._on_close is not None:
            self._on_close()
        self.app.pop_screen()
