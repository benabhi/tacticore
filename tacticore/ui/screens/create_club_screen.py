"""Pantalla "Crea tu club": el arranque de la partida (estilo ncurses).

Pide el nombre del manager (vos), del club, de la hinchada, del estadio y la
nacionalidad (que define en que liga se juega). Al costado se dibuja, EN VIVO
mientras se tipea el nombre del club, su identicon ASCII (emblema + color,
unicos por nombre).

Forma de la vieja escuela: un panel de texto con campos en una linea, el activo
resaltado (como el selector de paises); se escribe con el teclado, se mueve con
las flechas y se confirma/elige con Enter. Pantalla completa 80x25, sin scroll.
"""

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static

from ..identicon import identicon_color, render_identicon
from .base_screen import BaseScreen
from .country_select_screen import CountrySelectScreen

_LABELS = ["Manager", "Club", "Hinchada", "Estadio", "Nacionalidad"]
_CLUB = 1          # indice del campo "Club" (el que alimenta el identicon)
_NAT = 4           # indice del campo de nacionalidad (abre el selector)
_CREATE = 5        # indice del boton "Crear club"
_N = 6             # 4 campos de texto + nacionalidad + crear
_LBL_W = 14        # ancho de la columna de etiquetas
_ROW_W = 42        # ancho de la fila resaltada


class CreateClubScreen(BaseScreen):
    """Formulario de creacion del club (ncurses) con identicon en vivo."""

    CSS = """
    #viewport {
        align: center top;
    }
    #title {
        width: 1fr;
        text-align: center;
        color: green;
        text-style: bold;
        padding: 1 0 0 0;
    }
    #welcome {
        width: 1fr;
        text-align: center;
        padding: 1 2;
    }
    #cols {
        width: 72;
        height: auto;
    }
    #form {
        width: 46;
        height: auto;
    }
    #side {
        width: 24;
        height: auto;
        align: center top;
    }
    #ident_title {
        width: 24;
        height: 1;
        text-align: center;
        color: $text-muted;
    }
    #ident {
        width: 24;
        height: auto;
        text-align: center;
    }
    #ident_name {
        width: 24;
        height: 1;
        text-align: center;
        text-style: bold;
        text-overflow: ellipsis;
    }
    #footer {
        width: 1fr;
        text-align: center;
        color: $text-muted;
        padding: 1 0 0 0;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._texts = ["", "", "", ""]   # manager, club, hinchada, estadio
        self._country = None             # (nombre, codigo)
        self._active = 0

    def compose_viewport(self) -> ComposeResult:
        yield Static("CREA TU CLUB", id="title")
        yield Static(self._welcome_text(), id="welcome")
        with Horizontal(id="cols"):
            yield Static(self._form_text(), id="form")
            with Vertical(id="side"):
                yield Static("Emblema del club", id="ident_title")
                yield Static(render_identicon(""), id="ident")
                yield Static("", id="ident_name")
        yield Static(
            "Flechas: campo   Escribi: editar   Enter: elegir / crear", id="footer"
        )

    def _welcome_text(self) -> Text:
        w = Text(justify="center")
        w.append("Bienvenido a TACTICORE, manager.\n", style="bold green")
        w.append(
            "Vas a fundar tu club y arrancar el camino desde abajo, en el ascenso.\n",
            style="white",
        )
        w.append(
            "Dale su identidad: nombre, hinchada, estadio y bandera.",
            style="grey62",
        )
        return w

    # --- Render del formulario ---
    def _form_text(self) -> Text:
        t = Text()
        for i, label in enumerate(_LABELS):
            if i == _NAT:
                value = self._country[0] if self._country else "(Enter para elegir)"
            else:
                value = self._texts[i] + ("_" if i == self._active else "")
            line = label.ljust(_LBL_W) + value
            if i == self._active:
                t.append(("> " + line).ljust(_ROW_W) + "\n", style="bold black on green")
            else:
                t.append(("  " + line) + "\n", style="white")
        # Lineas en blanco para que CREAR CLUB quede en la MISMA fila que el nombre
        # del club bajo el identicon (titulo 1 + emblema 7 -> el nombre va en la
        # fila 8; los campos son 5, asi que 3 en blanco dejan CREAR en la fila 8).
        t.append("\n\n\n")
        crear = "> CREAR CLUB <" if self._active == _CREATE else "CREAR CLUB"
        style = "bold black on green" if self._active == _CREATE else "green"
        t.append(crear.center(_ROW_W), style=style)
        return t

    def _refresh(self) -> None:
        self.query_one("#form", Static).update(self._form_text())

    def _refresh_ident(self) -> None:
        name = self._texts[_CLUB]
        self.query_one("#ident", Static).update(render_identicon(name))
        label = self.query_one("#ident_name", Static)
        if name.strip():
            label.update(name.strip().upper())
            label.styles.color = identicon_color(name)
        else:
            label.update("")

    # --- Teclado: mover, editar, confirmar ---
    def on_key(self, event) -> None:
        key = event.key
        if key in ("down", "tab"):
            self._active = (self._active + 1) % _N
            event.stop()
            self._refresh()
        elif key in ("up", "shift+tab"):
            self._active = (self._active - 1) % _N
            event.stop()
            self._refresh()
        elif key == "enter":
            event.stop()
            self._activate()
        elif key == "backspace":
            if self._active < _NAT and self._texts[self._active]:
                self._texts[self._active] = self._texts[self._active][:-1]
                event.stop()
                self._refresh()
                if self._active == _CLUB:
                    self._refresh_ident()
        elif event.character and event.character.isprintable() and len(event.character) == 1:
            if self._active < _NAT and len(self._texts[self._active]) < 22:
                self._texts[self._active] += event.character
                event.stop()
                self._refresh()
                if self._active == _CLUB:
                    self._refresh_ident()

    def _activate(self) -> None:
        if self._active == _NAT:
            self.app.push_screen(CountrySelectScreen(), self._set_country)
        elif self._active == _CREATE:
            self._create()

    def _set_country(self, country) -> None:
        if country is None:
            return
        self._country = country
        self._refresh()

    def _create(self) -> None:
        from .office_screen import OfficeScreen

        app = self.app
        app.manager_name = self._texts[0].strip() or "Manager"
        app.club_name = self._texts[1].strip() or "Mi Club"
        app.club_fans = self._texts[2].strip() or "La Hinchada"
        app.club_stadium = self._texts[3].strip() or "El Estadio"
        app.club_country = self._country[1] if self._country else "ES"
        app.switch_screen(OfficeScreen())
