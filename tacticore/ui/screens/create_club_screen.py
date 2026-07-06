"""Pantalla "Crea tu club": el arranque de la partida (estilo ncurses).

Pide el nombre del manager (vos), del club, de la hinchada, del estadio, la
nacionalidad (que define en que liga se juega) y el patrocinador principal (se
elige entre 3 ofertas ahi mismo). Al costado se dibuja EN VIVO, mientras se tipea
el nombre del club, su identicon ASCII (emblema + color, unicos por nombre).

Forma de la vieja escuela: campos en una linea, el activo resaltado; se escribe
con el teclado, se mueve con las flechas, se cambia el patrocinador con izq/der y
se confirma/elige con Enter. La ayuda queda anclada al fondo. 80x25, sin scroll.
"""

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static

from ... import config
from ...core.rng import new_rng
from ...domain.enums import LeagueTier, Mentality
from ...domain.manager import Manager
from ...generators.club_generator import ClubGenerator
from ...generators.sponsor_generator import SponsorGenerator
from ...persistence import savegame
from ..format import hint, money
from ..identicon import identicon_color, render_identicon
from ..palette import MUTED
from .base_screen import BaseScreen
from .country_select_screen import CountrySelectScreen

_LABELS = ["Manager", "Club", "Hinchada", "Estadio", "Entrenador", "Nacionalidad"]
_CLUB = 1          # indice del campo "Club" (el que alimenta el identicon)
_COACH = 4         # indice del campo "Entrenador" (izq/der cambia la mentalidad)
_NAT = 5           # indice del campo de nacionalidad (abre el selector)
_SPONSOR = 6       # zona de eleccion de patrocinador (izq/der cambia la oferta)
_CREATE = 7        # indice del boton "Crear club"
_N = 8
_LBL_W = 14        # ancho de la columna de etiquetas
_ROW_W = 42        # ancho de la fila resaltada
_CARD_W = 54       # ancho de la tarjeta de patrocinadores (columna izquierda)

# Etiqueta del entrenador en masculino (el enum Mentality va en femenino porque
# describe la "mentalidad"; aca describe al entrenador).
_COACH_LABEL = {
    Mentality.OFFENSIVE: "Ofensivo", Mentality.NEUTRAL: "Neutral",
    Mentality.DEFENSIVE: "Defensivo",
}


class CreateClubScreen(BaseScreen):
    """Formulario de creacion del club (ncurses) con identicon y patrocinador."""

    CSS = """
    #viewport { align: center top; }
    #title {
        width: 1fr; text-align: center; color: green; text-style: bold;
        padding: 1 0 0 0;
    }
    #welcome { width: 1fr; text-align: center; padding: 1 2 0 2; }
    #status { width: 1fr; height: 1; text-align: center; margin: 1 0; }
    #cols { width: 78; height: auto; }
    #leftcol { width: 54; height: auto; }
    #form { width: 52; height: auto; }
    #sponsors { width: 54; height: auto; }
    #side { width: 24; height: auto; align: center top; }
    #ident_title { width: 24; height: 1; text-align: center; color: $text-muted; }
    #ident { width: 24; height: auto; text-align: center; }
    #ident_name {
        width: 24; height: 1; text-align: center; text-style: bold;
        text-overflow: ellipsis;
    }
    #crear { width: 1fr; height: auto; text-align: center; padding: 1 0 0 0; }
    #footer { dock: bottom; width: 1fr; text-align: center; }
    """

    def __init__(self) -> None:
        super().__init__()
        self._texts = ["", "", "", ""]   # manager, club, hinchada, estadio
        self._country = None             # (nombre, codigo)
        self._active = 0
        self._offers = None   # 3 ofertas de patrocinio (se generan al montar)
        self._sponsor = 0     # oferta elegida por defecto
        self._mentalities = list(Mentality)  # opciones del entrenador
        self._coach = self._mentalities.index(Mentality.NEUTRAL)  # mentalidad elegida

    def compose_viewport(self) -> ComposeResult:
        # El club arranca en la liga E; las 3 ofertas salen de la semilla (deterministas).
        self._offers = SponsorGenerator(new_rng(self.app.seed)).offers(LeagueTier.E, 3)
        yield Static("CREA TU CLUB", id="title")
        yield Static(self._welcome_text(), id="welcome")
        # Linea reservada (altura fija): guia por defecto, error en rojo si falta algo.
        yield Static(self._status_help(), id="status")
        with Horizontal(id="cols"):
            with Vertical(id="leftcol"):
                # El formulario (con lineas en blanco al final) empuja el bloque de
                # patrocinadores hasta la altura del nombre del club (bajo el emblema).
                yield Static(self._form_text(), id="form")
                yield Static(self._sponsors_text(), id="sponsors")
            with Vertical(id="side"):
                yield Static("Emblema del club", id="ident_title")
                yield Static(render_identicon(""), id="ident")
                yield Static("", id="ident_name")
        yield Static(self._crear_text(), id="crear")
        yield Static(self._footer_text(), id="footer")

    def _welcome_text(self) -> Text:
        w = Text(justify="center")
        w.append("Bienvenido a TACTICORE, manager.\n", style="bold green")
        w.append("Funda tu club desde abajo: dale identidad y firma tu patrocinador.",
                 style="grey62")
        return w

    def _footer_text(self) -> Text:
        return hint(("Flechas", "mover"), ("Escribi", "editar"),
                    ("<>", "cambiar"), ("Enter", "elegir / crear"))

    # --- Linea de estado: guia por defecto / error de validacion ---
    def _status_help(self) -> Text:
        return Text(
            "Todos los campos son obligatorios.", style="grey50", justify="center"
        )

    def _missing_fields(self) -> list[str]:
        """Etiquetas de los campos sin completar (texto vacio o sin pais)."""
        missing = [_LABELS[i] for i in range(_COACH) if not self._texts[i].strip()]
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

    # --- Render del formulario (los 5 campos) ---
    def _form_text(self) -> Text:
        t = Text()
        for i, label in enumerate(_LABELS):
            if i == _NAT:
                value = self._country[0] if self._country else "(Enter para elegir)"
            elif i == _COACH:
                value = f"< {_COACH_LABEL[self._mentalities[self._coach]]} >"
            else:
                value = self._texts[i] + ("_" if i == self._active else "")
            cell = label.ljust(_LBL_W)
            if i == self._active:
                t.append("> ", style="bold black on green")
                t.append(cell, style="black on green")
                t.append(value, style="bold black on green")
                used = 2 + len(cell) + len(value)
                if used < _ROW_W:
                    t.append(" " * (_ROW_W - used), style="on green")
                t.append("\n")
            else:
                t.append("  ")
                t.append(cell, style=MUTED)
                t.append(value + "\n", style="bold white")
        # Lineas en blanco: bajan el bloque PATROCINADOR hasta quedar a la altura del
        # nombre del club (emblema = titulo + 7 filas + nombre; los campos son 6).
        t.append("\n")
        return t

    def _sponsors_text(self) -> Text:
        active = self._active == _SPONSOR
        t = Text()
        t.append("PATROCINADOR", style="bold green")
        t.append("  (izq/der elige)\n" if active else "\n", style="grey62")
        for i, c in enumerate(self._offers):
            if c.promotion_bonus and c.streak_bonus:
                bonus = f"Asc {money(c.promotion_bonus)} +Racha"
            elif c.promotion_bonus:
                bonus = f"Ascenso {money(c.promotion_bonus)}"
            elif c.streak_bonus:
                bonus = f"Racha {money(c.streak_bonus)}"
            else:
                bonus = "sin bonus"
            row = (f"{c.sponsor.name}".ljust(12) + f"{c.weeks_total} sem".ljust(8)
                   + f"{money(c.weekly_pay)}/sem".ljust(12) + bonus)
            chosen = i == self._sponsor
            if chosen:
                style = "bold black on green" if active else "bold white"
                t.append(("> " + row)[:_CARD_W].ljust(_CARD_W) + "\n", style=style)
            else:
                t.append(("  " + row)[:_CARD_W] + "\n", style="grey62")
        return t

    def _crear_text(self) -> Text:
        crear = "> CREAR CLUB <" if self._active == _CREATE else "CREAR CLUB"
        style = "bold black on green" if self._active == _CREATE else "green"
        return Text(crear, style=style, justify="center")

    def _refresh(self) -> None:
        self.query_one("#form", Static).update(self._form_text())
        self.query_one("#sponsors", Static).update(self._sponsors_text())
        self.query_one("#crear", Static).update(self._crear_text())

    def _refresh_ident(self) -> None:
        name = self._texts[_CLUB]
        self.query_one("#ident", Static).update(render_identicon(name))
        label = self.query_one("#ident_name", Static)
        if name.strip():
            label.update(name.strip().upper())
            label.styles.color = identicon_color(name)
        else:
            label.update("")

    # --- Teclado: mover, editar, elegir patrocinador, confirmar ---
    def on_key(self, event) -> None:
        key = event.key
        if key in ("down", "tab"):
            self._active = (self._active + 1) % _N
            event.stop(); self._refresh()
        elif key in ("up", "shift+tab"):
            self._active = (self._active - 1) % _N
            event.stop(); self._refresh()
        elif key in ("left", "right") and self._active == _COACH:
            self._coach = (self._coach + (1 if key == "right" else -1)) % len(self._mentalities)
            event.stop(); self._refresh()
        elif key in ("left", "right") and self._active == _SPONSOR:
            self._sponsor = (self._sponsor + (1 if key == "right" else -1)) % len(self._offers)
            event.stop(); self._refresh()
        elif key == "enter":
            event.stop(); self._activate()
        elif key == "backspace":
            if self._active < _COACH and self._texts[self._active]:
                self._texts[self._active] = self._texts[self._active][:-1]
                event.stop(); self._refresh(); self._show_help()
                if self._active == _CLUB:
                    self._refresh_ident()
        elif event.character and event.character.isprintable() and len(event.character) == 1:
            if self._active < _COACH and len(self._texts[self._active]) < 22:
                self._texts[self._active] += event.character
                event.stop(); self._refresh(); self._show_help()
                if self._active == _CLUB:
                    self._refresh_ident()

    def _activate(self) -> None:
        if self._active == _NAT:
            available = [(c.name, c.code) for c in self.app.game.countries]
            self.app.push_screen(
                CountrySelectScreen(available, title="ELEGI LA NACIONALIDAD DE TU CLUB"),
                self._set_country,
            )
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

        missing = self._missing_fields()
        if missing:
            self._show_error(missing)
            return

        app = self.app
        game = app.game
        manager_name = self._texts[0].strip()
        country_code = self._country[1]
        first, _, last = manager_name.partition(" ")
        manager = Manager(first_name=first, last_name=last, nationality=country_code)
        club = ClubGenerator(new_rng(app.seed)).player_club(
            name=self._texts[1].strip(),
            fans_name=self._texts[2].strip(),
            stadium_name=self._texts[3].strip(),
            manager=manager,
            country_code=country_code,
            squad_size=config.SQUAD_SIZE,
            members=1500,
            today=game.calendar.current_date,
            coach_mentality=self._mentalities[self._coach],
        )
        game.install_player_club(club)
        game.manager_name = manager_name

        # Fixtures de TODAS las ligas (deterministas) para que el mundo progrese,
        # y los amistosos del jugador, para que aparezcan en Partidos desde el
        # arranque (sin esperar a avanzar el primer dia).
        from ...simulation.season import (
            ensure_all_fixtures, ensure_player_friendlies)

        ensure_all_fixtures(game)
        ensure_player_friendlies(game)

        # Patrocinador elegido: se firma aca mismo (primer cupo) y su bono de firma
        # entra a la caja. Los cupos que se desbloquean al ascender y las renovaciones
        # llegan despues como ofertas-evento en Notificaciones.
        chosen = self._offers[self._sponsor]
        club.sponsors = [chosen]
        club.capital += chosen.signing_bonus

        savegame.save_game(game)
        app.switch_screen(OfficeScreen())
