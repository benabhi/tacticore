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
from ..format import append_section, hint, money
from ..player_labels import (
    ATTR_GROUPS,
    ATTR_LABEL,
    CHARACTER_LABEL,
    FOOT_LABEL,
    INJURY_TYPE_LABEL,
    LEADERSHIP_LABEL,
    MORALE_LABEL,
    POSITION_LABEL,
    specialty_label,
)
from ..widgets.tab_bar import TabBar
from .base_screen import BaseScreen

_W = 76  # ancho util dentro del viewport
_MODE_NAMES = ("Normal", "Por puesto", "Por nivel")
_TABS = ("Datos", "Historial", "Trayectoria")

# Color de la moral (1 peor -> 5 mejor): de rojo a verde.
_MORALE_STYLE = {1: "bold red", 2: "red", 3: "yellow", 4: "green", 5: "bold green"}


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
        margin-top: 1;   /* separa las pestañas del contenido */
    }
    #hint {
        dock: bottom;    /* la ayuda siempre en la ultima linea */
        width: 76;
        text-align: center;
        color: $text-muted;
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

    def _hint_text(self) -> Text:
        return hint(
            ("Esc", "volver"), ("<- ->", "jugador"), ("1-3", "pestana"),
            ("c", f"color ({_MODE_NAMES[self._color_mode]})"),
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
        # --- Encabezado: nombre (+ alias) a la izquierda; posicion y dorsal a la
        # derecha (la posicion se pliega aca para ahorrar una fila). ---
        name = p.full_name
        if p.nickname:
            name += f'  "{p.nickname}"'
        dorsal = f"Dorsal {p.shirt_number}" if p.shirt_number else "Sin dorsal"
        right = f"{POSITION_LABEL[p.position]} ({p.position.value})   {dorsal}"
        t.append(name[: _W - len(right)].ljust(_W - len(right)), style="bold white")
        t.append(right + "\n", style="yellow")
        t.append("-" * _W + "\n", style="grey50")

        # --- Franja resumen: numeros clave, valor coloreado por nivel. ---
        self._summary_strip(t, p)
        t.append("-" * _W + "\n", style="grey50")

        # --- Detalle en dos columnas con titulos, valores alineados. ---
        years, days = p.age_parts_on(self._today)
        # Fragilidad: propension a lesionarse (baja = aguanta; alta = se rompe seguido).
        ip = p.injury_proneness
        frag = "Baja" if ip < 35 else "Media" if ip < 65 else "Alta"
        frag_style = "green" if ip < 35 else "yellow" if ip < 65 else "red"
        identidad = [
            ("Nacionalidad", p.nationality),
            ("Pie", FOOT_LABEL[p.foot]),
            ("Edad", f"{years} anios {days} dias"),
            ("Nacimiento", p.birth_date.strftime("%d-%m-%Y")),
            ("Altura", f"{p.height_cm} cm"),
            ("Peso", f"{p.weight_kg} kg"),
            ("Fragilidad", frag, frag_style),
            ("Cantera", p.origin_club or "-"),
        ]
        if p.injury is None:
            lesion, lesion_style = "Sano", "green"
        else:
            lesion = f"{INJURY_TYPE_LABEL[p.injury.type]} - {p.injury_weeks_left(self._today)} sem"
            lesion_style = "red"
        if p.matches_suspended > 0:
            sancion = f"Suspendido ({p.matches_suspended} partido/s)"
            sancion_style = "red"
        elif p.yellow_cards > 0:
            sancion, sancion_style = f"{p.yellow_cards} amarilla(s)", "yellow"
        else:
            sancion, sancion_style = "Sin sanciones", "grey62"
        ficha = [
            ("Sueldo", money(player_salary(p, self._today)), "white"),
            ("Experiencia", f"{p.experience:.0f}", "white"),
            ("Moral", f"{MORALE_LABEL[p.morale]} ({p.morale.value})",
             _MORALE_STYLE.get(p.morale.value, "white")),
            ("Liderazgo", f"{LEADERSHIP_LABEL[p.leadership]} ({p.leadership})",
             _MORALE_STYLE.get(p.leadership, "white")),
            ("Caracter", f"{CHARACTER_LABEL[p.character]} ({p.character})",
             _MORALE_STYLE.get(p.character, "white")),
            ("Especialidad", specialty_label(p.specialty), "white"),
            ("Lesion", lesion, lesion_style),
            ("Sancion", sancion, sancion_style),
        ]
        self._two_columns(t, ("IDENTIDAD", identidad), ("FICHA", ficha))

        # --- Atributos (grilla de 3 columnas, sin cambios de fondo). ---
        t.append("-" * _W + "\n", style="grey50")
        self._attributes(t)
        return t

    def _summary_strip(self, t: Text, p) -> None:
        """Franja de numeros clave: etiqueta en verde, valor coloreado por nivel."""
        items = [
            ("OVR", f"{p.overall:.1f}", _value_style(p.overall)),
            ("POT", f"{p.potential:.1f}", _value_style(p.potential)),
            ("FORMA", f"{p.form:.1f}", _value_style(p.form)),
            ("FIT", f"{p.fitness:.0f}", _value_style(p.fitness)),
            ("VALOR", money(player_value(p, self._today)), "bold white"),
        ]
        t.append("  ")
        for i, (label, value, style) in enumerate(items):
            if i:
                t.append("    ")
            t.append(f"{label} ", style="bold green")
            t.append(value, style=style)
        t.append("\n")

    def _two_columns(self, t: Text, left, right) -> None:
        """Dos columnas 'Etiqueta valor' con titulo verde y valor en columna fija.

        `left`/`right` = (titulo, filas); cada fila es (label, value) o
        (label, value, estilo) para colorear el valor.
        """
        half = _W // 2          # ancho de cada columna
        label_w = 14            # los valores arrancan todos en la misma columna
        ltitle, lrows = left
        rtitle, rrows = right

        def cell(row) -> Text:
            label, value = row[0], row[1]
            style = row[2] if len(row) > 2 else "white"
            c = Text()
            c.append(f"{label:<{label_w}}", style="grey62")
            c.append(str(value), style=style)
            return c

        head = Text()
        head.append(ltitle.ljust(half), style="bold green")
        head.append(rtitle, style="bold green")
        head.append("\n")
        t.append_text(head)

        for i in range(max(len(lrows), len(rrows))):
            line = Text()
            if i < len(lrows):
                lc = cell(lrows[i])
                line.append_text(lc)
                line.append(" " * max(1, half - len(lc.plain)))
            else:
                line.append(" " * half)
            if i < len(rrows):
                line.append_text(cell(rrows[i]))
            line.append("\n")
            t.append_text(line)

    def _attributes(self, t: Text) -> None:
        col_w = 25  # 3 columnas x 25 = 75
        for title, _attrs in ATTR_GROUPS:
            t.append(title.ljust(col_w), style="bold green")
        t.append("\n")

        priorities = POSITION_PRIORITIES[self._player.position]
        gains = self._player.last_gains
        rows = max(len(attrs) for _, attrs in ATTR_GROUPS)
        for i in range(rows):
            for _title, attrs in ATTR_GROUPS:
                if i >= len(attrs):
                    t.append(" " * col_w)
                    continue
                attr = attrs[i]
                value = getattr(self._player, attr)
                base = ATTR_LABEL[attr].ljust(13) + f"{value:.1f}".rjust(5)   # 18 chars
                t.append(base, style=self._attr_style(attr, value, priorities))
                # Lo que gano en el ULTIMO entrenamiento, en verde (se resetea cada entreno).
                gain = gains.get(attr, 0.0)
                extra = f" +{gain:.1f}" if gain > 0 else ""
                if extra:
                    t.append(extra, style="bold green")
                t.append(" " * (col_w - len(base) - len(extra)))
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
