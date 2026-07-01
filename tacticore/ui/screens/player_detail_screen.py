"""Ficha completa de un jugador, con pestañas, en 80x25.

Se abre desde la tabla de plantilla (Enter sobre una fila). Pestañas:
- Datos: identidad, estado (incluye Valor y Sueldo) y atributos.
- Historial: goles, tarjetas, lesiones (placeholder).
- Trayectoria: clubes por los que paso (placeholder).

Teclas: Esc/Enter volver; flechas izquierda/derecha rotan al jugador
anterior/siguiente; 1/2/3 (o Tab) cambian de pestaña; `c` cicla el coloreo de los
atributos (Normal / Por puesto / Por nivel) en la pestaña Datos.
"""

from datetime import date

from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Static

from ...domain.positions import POSITION_PRIORITIES
from ...simulation.economy import player_salary, player_value
from ..format import append_section, money
from ..player_labels import (
    ATTR_GROUPS,
    ATTR_LABEL,
    FOOT_LABEL,
    MORALE_LABEL,
    POSITION_LABEL,
    specialty_label,
)
from ..widgets.tab_bar import TabBar
from .base_screen import BaseScreen

_W = 76  # ancho util dentro del viewport
_MODE_NAMES = ("Normal", "Por puesto", "Por nivel")
_TABS = ("Datos", "Historial", "Trayectoria")


def _value_style(value: float) -> str:
    """Color de un atributo segun su valor (gradiente verde -> rojo)."""
    if value >= 80:
        return "bold green"
    if value >= 65:
        return "green"
    if value >= 50:
        return "yellow"
    if value >= 35:
        return "orange1"
    return "red"


class PlayerDetailScreen(BaseScreen):
    """Ficha de un jugador con pestañas, navegable y con coloreo."""

    BINDINGS = [
        ("escape", "back", "Volver"),
        ("backspace", "back", "Volver"),
        ("enter", "back", "Volver"),
        ("left", "prev", "Anterior"),
        ("right", "next", "Siguiente"),
        ("c", "color", "Color"),
    ]

    CSS = """
    #viewport {
        align: center top;
    }
    #dtabs {
        width: 76;
        margin-top: 1;
    }
    #card {
        width: 76;
        height: auto;
    }
    #hint {
        width: 76;
        text-align: center;
        color: $text-muted;
        margin-top: 1;
    }
    """

    def __init__(self, players: list, index: int, today: date, on_close=None) -> None:
        super().__init__()
        self._players = players
        self._index = index
        self._today = today
        self._on_close = on_close
        self._color_mode = 0
        self._tab = 0

    @property
    def _player(self):
        return self._players[self._index]

    def compose_viewport(self) -> ComposeResult:
        yield TabBar(_TABS, id="dtabs")
        yield Static(self._card_text(), id="card")
        yield Static(self._hint_text(), id="hint")

    def _refresh(self) -> None:
        self.query_one("#card", Static).update(self._card_text())
        self.query_one("#hint", Static).update(self._hint_text())

    def _hint_text(self) -> str:
        return (
            f"Esc: volver   <- ->: jugador   1-3: pestaña   "
            f"c: color ({_MODE_NAMES[self._color_mode]})"
        )

    # --- Contenido segun pestaña ---
    def _card_text(self) -> Text:
        if self._tab == 1:
            return self._history_text()
        if self._tab == 2:
            return self._career_text()
        return self._data_text()

    def _history_text(self) -> Text:
        t = Text()
        append_section(t, "HISTORIAL", [
            ("Todavia no hay eventos.", "grey62"),
            "",
            ("Aca vas a ver los hitos del jugador: goles, asistencias,", "grey62"),
            ("tarjetas y lesiones, a medida que se jueguen los partidos.", "grey62"),
        ])
        return t

    def _career_text(self) -> Text:
        p = self._player
        t = Text()
        append_section(t, "TRAYECTORIA", [
            (f"Cantera: {p.origin_club or '-'}", "white"),
            "",
            ("El paso del jugador por distintos clubes (fichajes y cesiones)", "grey62"),
            ("se registrara aca cuando exista el mercado de pases.", "grey62"),
        ])
        return t

    def _data_text(self) -> Text:
        p = self._player
        t = Text()
        # Encabezado: nombre (+ alias) y dorsal.
        name = p.full_name
        if p.nickname:
            name += f'  "{p.nickname}"'
        dorsal = f"Dorsal {p.shirt_number}" if p.shirt_number else "Sin dorsal"
        t.append(name.ljust(_W - len(dorsal)), style="bold white")
        t.append(dorsal + "\n", style="yellow")
        t.append("-" * _W + "\n", style="grey50")

        t.append(
            f"  Posicion: {POSITION_LABEL[p.position]} ({p.position.value})\n",
            style="white",
        )
        years, days = p.age_parts_on(self._today)
        born = p.birth_date.strftime("%d-%m-%Y")
        self._kv_rows(t, [
            ("Nacionalidad", p.nationality, "Pie", FOOT_LABEL[p.foot]),
            ("Edad", f"{years} anios {days} dias", "Nacimiento", born),
            ("Altura", f"{p.height_cm} cm", "Peso", f"{p.weight_kg} kg"),
            ("Cantera", p.origin_club or "-", "", ""),
        ])
        t.append("\n")

        # Estado, economia y rasgos.
        self._kv_rows(t, [
            ("Media (OVR)", f"{p.overall:.1f}", "Potencial", f"{p.potential:.1f}"),
            ("Forma", f"{p.form:.1f}", "Fitness", f"{p.fitness:.1f}"),
            ("Experiencia", f"{p.experience:.0f}", "Moral", MORALE_LABEL[p.morale]),
            ("Valor", money(player_value(p, self._today)),
             "Sueldo", money(player_salary(p, self._today))),
            ("Especialidad", specialty_label(p.specialty),
             "Prop. lesion", f"{p.injury_proneness:.0f}"),
            ("Lesion", "Sano" if p.injury is None else "Lesionado", "", ""),
        ])
        t.append("\n")

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
        for title, _attrs in ATTR_GROUPS:
            t.append(title.ljust(col_w), style="bold green")
        t.append("\n")

        priorities = POSITION_PRIORITIES[self._player.position]
        rows = max(len(attrs) for _, attrs in ATTR_GROUPS)
        for i in range(rows):
            for _title, attrs in ATTR_GROUPS:
                if i >= len(attrs):
                    t.append(" " * col_w)
                    continue
                attr = attrs[i]
                value = getattr(self._player, attr)
                cell = (ATTR_LABEL[attr].ljust(13) + f"{value:.1f}".rjust(5)).ljust(col_w)
                t.append(cell, style=self._attr_style(attr, value, priorities))
            if i < rows - 1:  # sin salto final: evita una linea vacia que desborda
                t.append("\n")

    def _attr_style(self, attr: str, value: float, priorities) -> str:
        if self._color_mode == 1:
            return "bold cyan" if attr in priorities else "grey50"
        if self._color_mode == 2:
            return _value_style(value)
        return "white"

    # --- Navegacion ---
    def _set_tab(self, index: int) -> None:
        if index == self._tab or not (0 <= index < len(_TABS)):
            return
        self._tab = index
        self.query_one("#dtabs", TabBar).set_active(index)
        self._refresh()

    def on_key(self, event) -> None:
        key = event.key
        if key in ("1", "2", "3"):
            event.stop()
            self._set_tab(int(key) - 1)
        elif key == "tab":
            event.stop()
            self._set_tab((self._tab + 1) % len(_TABS))
        elif key == "shift+tab":
            event.stop()
            self._set_tab((self._tab - 1) % len(_TABS))

    def action_prev(self) -> None:
        self._index = (self._index - 1) % len(self._players)
        self._refresh()

    def action_next(self) -> None:
        self._index = (self._index + 1) % len(self._players)
        self._refresh()

    def action_color(self) -> None:
        self._color_mode = (self._color_mode + 1) % len(_MODE_NAMES)
        self._refresh()

    def action_back(self) -> None:
        if self._on_close is not None:
            self._on_close(self._index)
        self.app.pop_screen()
