"""Ficha completa de un jugador: todos sus datos, bien formateados en 80x25.

Se abre desde la tabla de plantilla (Enter sobre una fila). Se vuelve con Esc /
Enter / Backspace. Es una pantalla aparte que se apila encima; al volver, la
tabla queda como estaba.
"""

from datetime import date

from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Static

from ..player_labels import (
    ATTR_GROUPS,
    ATTR_LABEL,
    FOOT_LABEL,
    MORALE_LABEL,
    POSITION_LABEL,
    specialty_label,
)
from .base_screen import BaseScreen

_W = 76  # ancho util dentro del viewport


class PlayerDetailScreen(BaseScreen):
    """Ficha de un jugador con todos sus datos."""

    BINDINGS = [
        ("escape", "back", "Volver"),
        ("backspace", "back", "Volver"),
        ("enter", "back", "Volver"),
    ]

    CSS = """
    #viewport {
        align: center top;
    }
    #card {
        width: 76;
        height: auto;
        margin-top: 1;
    }
    #hint {
        width: 76;
        text-align: center;
        color: $text-muted;
        margin-top: 1;
    }
    """

    def __init__(self, player, today: date) -> None:
        super().__init__()
        self._player = player
        self._today = today

    def compose_viewport(self) -> ComposeResult:
        yield Static(self._card_text(), id="card")
        yield Static("Esc / Enter: volver a la plantilla", id="hint")

    def _card_text(self) -> Text:
        p = self._player
        t = Text()
        t.append("FICHA DEL JUGADOR\n\n", style="bold green")

        # Encabezado: nombre (+ alias) y dorsal.
        name = p.full_name
        if p.nickname:
            name += f'  "{p.nickname}"'
        dorsal = f"Dorsal {p.shirt_number}" if p.shirt_number else "Sin dorsal"
        t.append(name.ljust(_W - len(dorsal)), style="bold white")
        t.append(dorsal + "\n", style="yellow")
        t.append("-" * _W + "\n", style="grey50")

        # Identidad (dos columnas de pares etiqueta/valor).
        age = p.age_on(self._today)
        self._kv_rows(t, [
            ("Posicion", POSITION_LABEL[p.position], "Nacionalidad", p.nationality),
            ("Edad", f"{age} ({p.birth_date.isoformat()})", "Pie", FOOT_LABEL[p.foot]),
            ("Altura", f"{p.height_cm} cm", "Peso", f"{p.weight_kg} kg"),
            ("Cantera", p.origin_club or "-", "", ""),
        ])
        t.append("\n")

        # Estado y rasgos.
        self._kv_rows(t, [
            ("Media (OVR)", f"{p.overall:.1f}", "Potencial", f"{p.potential:.1f}"),
            ("Forma", f"{p.form:.1f}", "Fitness", f"{p.fitness:.1f}"),
            ("Moral", MORALE_LABEL[p.morale], "Especialidad", specialty_label(p.specialty)),
            ("Lesion", "Sano" if p.injury is None else "Lesionado",
             "Prop. lesion", f"{p.injury_proneness:.0f}"),
        ])
        t.append("\n")

        # Atributos en cuatro columnas (fisicos / tecnicos / mentales / arquero).
        self._attributes(t)

        return t

    def _kv_rows(self, t: Text, rows) -> None:
        """Agrega filas con hasta dos pares 'Etiqueta: valor' por linea."""
        half = _W // 2
        for l1, v1, l2, v2 in rows:
            left = f"{l1}: {v1}" if l1 else ""
            right = f"{l2}: {v2}" if l2 else ""
            t.append("  " + left.ljust(half - 2), style="white")
            t.append(right + "\n", style="white")

    def _attributes(self, t: Text) -> None:
        col_w = 25  # 3 columnas x 25 = 75

        # Titulos de las cuatro columnas (fisicos / tecnicos / mentales / arquero).
        for title, _attrs in ATTR_GROUPS:
            t.append(title.ljust(col_w), style="bold green")
        t.append("\n")

        rows = max(len(attrs) for _, attrs in ATTR_GROUPS)
        for i in range(rows):
            for _title, attrs in ATTR_GROUPS:
                t.append(self._attr_cell(attrs, i, col_w), style="white")
            t.append("\n")

    def _attr_cell(self, attrs, i: int, col_w: int) -> str:
        """Celda 'Etiqueta   valor' de ancho fijo (vacia si no hay atributo)."""
        if i >= len(attrs):
            return " " * col_w
        attr = attrs[i]
        value = f"{getattr(self._player, attr):.1f}"
        return (ATTR_LABEL[attr].ljust(13) + value.rjust(5)).ljust(col_w)

    def action_back(self) -> None:
        self.app.pop_screen()
