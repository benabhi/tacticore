"""Pantalla "Crea tu club": el arranque de la partida (estilo ncurses).

Pide el nombre del presidente (vos), del club, de la hinchada, del estadio y la
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

from ... import config
from ...core.rng import new_rng
from ...domain.president import President
from ...generators.club_generator import ClubGenerator
from ...persistence import savegame
from ..identicon import identicon_color, render_identicon
from ..palette import MUTED
from .base_screen import BaseScreen
from .country_select_screen import CountrySelectScreen

_LABELS = ["Presidente", "Club", "Hinchada", "Estadio", "Nacionalidad"]
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
        padding: 1 2 0 2;
    }
    #status {
        width: 1fr;
        height: 1;
        text-align: center;
        margin: 1 0;
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
        self._texts = ["", "", "", ""]   # presidente, club, hinchada, estadio
        self._country = None             # (nombre, codigo)
        self._active = 0

    def compose_viewport(self) -> ComposeResult:
        yield Static("CREA TU CLUB", id="title")
        yield Static(self._welcome_text(), id="welcome")
        # Linea reservada (altura fija): guia por defecto, error en rojo si falta
        # algun campo. Siempre ocupa 1 fila, asi el error no desplaza nada.
        yield Static(self._status_help(), id="status")
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
        w.append("Bienvenido a TACTICORE, presidente.\n", style="bold green")
        w.append(
            "Vas a fundar tu club y arrancar el camino desde abajo, en el ascenso.\n",
            style="white",
        )
        w.append(
            "Dale su identidad: nombre, hinchada, estadio y bandera.",
            style="grey62",
        )
        return w

    # --- Linea de estado: guia por defecto / error de validacion ---
    def _status_help(self) -> Text:
        return Text(
            "Todos los campos son obligatorios.", style="grey50", justify="center"
        )

    def _missing_fields(self) -> list[str]:
        """Etiquetas de los campos sin completar (texto vacio o sin pais)."""
        missing = [_LABELS[i] for i in range(_NAT) if not self._texts[i].strip()]
        if self._country is None:
            missing.append(_LABELS[_NAT])
        return missing

    def _show_help(self) -> None:
        self.query_one("#status", Static).update(self._status_help())

    def _show_error(self, missing: list[str]) -> None:
        msg = "Falta completar: " + ", ".join(missing)
        self.query_one("#status", Static).update(
            Text(msg, style="bold red", justify="center")
        )

    # --- Render del formulario ---
    def _form_text(self) -> Text:
        # El LABEL va tenue y el VALOR (lo que escribis) en blanco/negrita, para
        # distinguir que tipeaste vos. El campo activo ademas va resaltado.
        t = Text()
        for i, label in enumerate(_LABELS):
            if i == _NAT:
                value = self._country[0] if self._country else "(Enter para elegir)"
            else:
                value = self._texts[i] + ("_" if i == self._active else "")
            cell = label.ljust(_LBL_W)
            if i == self._active:
                t.append("> ", style="bold black on green")
                t.append(cell, style="black on green")            # label
                t.append(value, style="bold black on green")      # valor (negrita)
                used = 2 + len(cell) + len(value)
                if used < _ROW_W:
                    t.append(" " * (_ROW_W - used), style="on green")
                t.append("\n")
            else:
                t.append("  ")
                t.append(cell, style=MUTED)                       # label tenue
                t.append(value + "\n", style="bold white")        # valor claro
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
                self._show_help()
                if self._active == _CLUB:
                    self._refresh_ident()
        elif event.character and event.character.isprintable() and len(event.character) == 1:
            if self._active < _NAT and len(self._texts[self._active]) < 22:
                self._texts[self._active] += event.character
                event.stop()
                self._refresh()
                self._show_help()
                if self._active == _CLUB:
                    self._refresh_ident()

    def _activate(self) -> None:
        if self._active == _NAT:
            # Solo se puede elegir un pais que exista en el mundo generado.
            available = [(c.name, c.code) for c in self.app.game.countries]
            self.app.push_screen(CountrySelectScreen(available), self._set_country)
        elif self._active == _CREATE:
            self._create()

    def _set_country(self, country) -> None:
        if country is None:
            return
        self._country = country
        self._refresh()
        self._show_help()

    def _create(self) -> None:
        from .office_screen import OfficeScreen

        # Todos los campos son obligatorios: si falta alguno, mostramos el error
        # en la linea reservada y no avanzamos.
        missing = self._missing_fields()
        if missing:
            self._show_error(missing)
            return

        app = self.app
        game = app.game
        president_name = self._texts[0].strip()
        country_code = self._country[1]

        # Presidente humano (sin edad: no se la pedimos).
        first, _, last = president_name.partition(" ")
        president = President(
            first_name=first, last_name=last, nationality=country_code
        )
        # Construir el club humilde del jugador (liga E, 500 socios) e insertarlo
        # en su pais reemplazando a un club IA.
        club = ClubGenerator(new_rng(app.seed)).player_club(
            name=self._texts[1].strip(),
            fans_name=self._texts[2].strip(),
            stadium_name=self._texts[3].strip(),
            president=president,
            country_code=country_code,
            squad_size=config.SQUAD_SIZE,
            today=game.calendar.current_date,
        )
        game.install_player_club(club)
        game.president_name = president_name

        # Guardar la partida (autosave) y entrar a la Oficina.
        savegame.save_game(game)
        app.switch_screen(OfficeScreen())
