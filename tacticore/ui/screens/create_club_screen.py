"""Pantalla "Crea tu club": el arranque de la partida.

Pide el nombre del club, de la hinchada y del estadio, y la nacionalidad (que
define en que liga se juega). Al costado se dibuja, EN VIVO mientras se tipea el
nombre, el identicon ASCII del club (su emblema y color, unicos por nombre).

Es de pantalla completa (80x25, sin scroll, directiva 1). Al confirmar guarda
los datos en la app y entra a la Oficina.
"""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Input, Static

from ..identicon import identicon_color, render_identicon
from .base_screen import BaseScreen
from .country_select_screen import CountrySelectScreen


class CreateClubScreen(BaseScreen):
    """Formulario de creacion del club con identicon en vivo."""

    CSS = """
    #viewport {
        align: center top;
    }
    #title {
        width: 1fr;
        text-align: center;
        color: green;
        text-style: bold;
    }
    #cols {
        width: 78;
        height: auto;
        padding: 1 0 0 0;
    }
    #form {
        width: 48;
        height: auto;
    }
    #side {
        width: 30;
        height: auto;
        align: center top;
    }
    .field {
        color: white;
    }
    Input {
        border: ascii green;
        width: 1fr;
        height: 3;
    }
    #side > #ident {
        width: auto;
        height: auto;
    }
    #ident_name {
        width: 1fr;
        text-align: center;
        text-style: bold;
    }
    #nat_btn, #create_btn {
        width: 1fr;
        height: 1;
        border: none;
        margin: 0;
    }
    #nat_label {
        width: 1fr;
        text-align: center;
        color: white;
    }
    #create_btn {
        margin: 1 0 0 0;
        color: black;
        background: green;
    }
    #footer {
        width: 1fr;
        text-align: center;
        color: $text-muted;
    }
    """

    def compose_viewport(self) -> ComposeResult:
        yield Static("CREA TU CLUB", id="title")
        with Horizontal(id="cols"):
            with Vertical(id="form"):
                yield Static("Nombre del club", classes="field")
                yield Input(placeholder="Real Zarist", id="club")
                yield Static("Nombre de la hinchada", classes="field")
                yield Input(placeholder="La Banda del Zar", id="fans")
                yield Static("Nombre del estadio", classes="field")
                yield Input(placeholder="Estadio Monumental", id="stadium")
                yield Static("Nacionalidad (define tu liga)", classes="field")
                yield Button("Elegir nacionalidad", id="nat_btn")
                yield Static("Sin elegir", id="nat_label")
            with Vertical(id="side"):
                yield Static(render_identicon(""), id="ident")
                yield Static("", id="ident_name")
        yield Button("Crear club", id="create_btn", variant="success")
        yield Static("Tab: campo siguiente   Enter en un campo: confirmar", id="footer")

    def on_mount(self) -> None:
        self._country = None  # (nombre, codigo)
        self.query_one("#club", Input).focus()

    # --- Identicon en vivo segun el nombre del club ---
    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "club":
            name = event.value
            self.query_one("#ident", Static).update(render_identicon(name))
            label = self.query_one("#ident_name", Static)
            if name.strip():
                label.update(name.strip().upper())
                label.styles.color = identicon_color(name)
            else:
                label.update("")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "nat_btn":
            self.app.push_screen(CountrySelectScreen(), self._set_country)
        elif event.button.id == "create_btn":
            self._create()

    def _set_country(self, country) -> None:
        """Callback del selector de pais: (nombre, codigo) o None si se cancelo."""
        if country is None:
            return
        self._country = country
        self.query_one("#nat_label", Static).update(f"> {country[0]} <")

    def _create(self) -> None:
        from .office_screen import OfficeScreen

        app = self.app
        app.club_name = self.query_one("#club", Input).value.strip() or "Mi Club"
        app.club_fans = self.query_one("#fans", Input).value.strip() or "La Hinchada"
        app.club_stadium = self.query_one("#stadium", Input).value.strip() or "El Estadio"
        app.club_country = self._country[1] if self._country else "ES"
        app.switch_screen(OfficeScreen())
