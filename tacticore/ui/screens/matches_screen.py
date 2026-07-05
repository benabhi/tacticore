"""Seccion Partidos: los encuentros del club y la competicion.

Pestañas:
- Proximos: los proximos partidos con su FECHA, tipo y si tienen tactica. Lista
  navegable (arriba/abajo) y PAGINADA; con Enter se abre la tactica de ESE partido.
- Liga: la tabla de posiciones, el fixture y las stats de la division (el panel
  `LeaguePanel`, que antes era la seccion Liga).
- Copa: por ahora un aviso (no se participa en ningun torneo).
- Historial: partidos ya jugados del club (del mas nuevo al mas viejo), paginado.

Layout de las tablas (Proximos/Historial): la TABLA queda arriba y la ayuda ABAJO,
pegada al menu (tabs / espacio / tabla / espacio / ayuda / espacio / menu). En vez
de desplazarse, se divide en PAGINAS (izq/der), como en Jugadores. La pestaña Liga
trae su propio layout (con la ayuda inline en sus titulos).
"""

from datetime import date

from rich.text import Text

from ..format import append_section, hint
from .league_panel import LeaguePanel
from .section_screen import SectionScreen

_LIGA_TAB, _COPA_TAB, _HIST_TAB = 1, 2, 3

_WIDTH = 78

# Geometria del area de contenido (25 - barra - separador - pestañas - menu - 1 de
# padding superior = 20 filas). Se reparten en: encabezado + regla (2), la pagina
# de datos (_PAGE_SIZE), un blanco, la ayuda y un blanco final (separan del menu).
_PAGE_SIZE = 15

# Color por tipo de partido (para leer de un vistazo de que competicion es).
_KIND_STYLE = {"Liga": "green", "Amistoso": "grey70", "Copa": "yellow"}

# Columnas de la lista de proximos: (titulo, ancho, alineacion).
_COLUMNS = [
    ("FECHA", 10, "l"), ("TIPO", 9, "l"), ("RIVAL", 30, "l"),
    ("SEDE", 7, "l"), ("TACTICA", 8, "l"),
]


class MatchesScreen(SectionScreen):
    """Proximos partidos (navegables, paginados) e historial del club."""

    section_key = "P"
    section_title = "Partidos"
    tabs = ("Proximos", "Liga", "Copa", "Historial")

    def __init__(self) -> None:
        super().__init__()
        self._selected = 0   # indice del partido resaltado en Proximos
        self._hist_page = 0  # pagina del Historial (0 = mas recientes)
        self._league_panel = LeaguePanel(self)  # la pestaña Liga

    @property
    def _club(self):
        game = self.app.game
        return game.player_club if game else None

    @property
    def _league(self):
        game = self.app.game
        return game.player_league if game else None

    def _club_matches(self):
        league, club = self._league, self._club
        if club is None:
            return []
        game = self.app.game
        league_matches = league.matches if league is not None else []
        # Liga + amistosos del jugador, ordenados por fecha (no por jornada: las
        # numeraciones de liga y amistoso se solaparian).
        mine = [m for m in league_matches if m.home is club or m.away is club]
        mine += list(game.friendlies) if game else []
        return sorted(mine, key=lambda m: (m.match_date or date.max, m.matchday))

    def _upcoming(self):
        return [m for m in self._club_matches() if not m.played]

    def _history(self):
        club = self._club
        played = [m for m in self._club_matches() if m.played] if club else []
        return list(reversed(played))  # del mas nuevo al mas viejo

    @staticmethod
    def _pages(total: int) -> int:
        return max(1, (total + _PAGE_SIZE - 1) // _PAGE_SIZE)

    # --- Ensamblado: tabla arriba, ayuda abajo (pegada al menu) ---
    def render_tab(self, index: int) -> Text:
        if index == _LIGA_TAB:
            return self._league_panel.render()   # trae su propio layout/ayuda
        if index == _COPA_TAB:
            return self._copa_text()
        if index == _HIST_TAB:
            table, page, pages = self._history_page()
            help_line = hint(("1-4", "pestana"), ("izq/der", "pagina"))
        else:
            table, page, pages = self._upcoming_page()
            help_line = hint(("arr/aba", "elegir partido"), ("Enter", "armar tactica"),
                             ("izq/der", "pagina"))
        if pages > 1:
            help_line.append(f"   Pag {page}/{pages}", style="grey62")
        return self._frame(table, help_line)

    def _copa_text(self) -> Text:
        t = Text()
        append_section(t, "COPA", [
            ("No estas participando en ningun torneo de copa por el momento.", "grey62"),
            "",
            ("Las copas nacionales e internacionales llegaran mas adelante.", "grey50"),
        ])
        return t

    def _frame(self, table_lines: list[Text], help_line: Text) -> Text:
        """Une la tabla (arriba) con la ayuda (abajo): encabezado + pagina, un blanco,
        la ayuda y un blanco final (que la separa del menu)."""
        out = Text()
        for line in table_lines:
            out.append_text(line if isinstance(line, Text) else Text(str(line)))
            out.append("\n")
        out.append("\n")            # espacio entre la tabla y la ayuda
        out.append_text(help_line)  # ayuda pegada al menu (un blanco la separa)
        return out

    # --- Proximos (navegable, paginado) ---
    def _upcoming_page(self):
        club = self._club
        if club is None:
            return [Text("Sin club todavia.", style="white")], 1, 1
        upcoming = self._upcoming()
        if not upcoming:
            return [Text("No hay proximos partidos.", style="grey62")], 1, 1

        self._selected = max(0, min(len(upcoming) - 1, self._selected))
        pages = self._pages(len(upcoming))
        page = self._selected // _PAGE_SIZE
        start = page * _PAGE_SIZE
        rows = list(enumerate(upcoming))[start:start + _PAGE_SIZE]

        lines = self._table_header()
        for i, m in rows:
            lines.append(self._match_row(m, club, i == self._selected))
        lines += [Text("")] * (_PAGE_SIZE - len(rows))  # relleno hasta la pagina llena
        return lines, page + 1, pages

    def _table_header(self) -> list[Text]:
        cells = [f"{h:<{w}}" if a == "l" else f"{h:>{w}}" for h, w, a in _COLUMNS]
        return [
            Text("  " + " ".join(cells), style="bold green"),
            Text("-" * _WIDTH, style="grey50"),
        ]

    def _match_row(self, m, club, selected: bool) -> Text:
        when = m.match_date.strftime("%d-%m-%Y") if m.match_date else f"J{m.matchday}"
        rival = m.away if m.home is club else m.home
        sede = "Local" if m.home is club else "Visita"
        has_tactic = m.tactic is not None
        values = [when, m.kind.value, rival.name, sede, "Si" if has_tactic else "No"]
        cells = [
            (str(v)[:w].ljust(w) if a == "l" else str(v)[:w].rjust(w))
            for v, (_, w, a) in zip(values, _COLUMNS)
        ]
        if selected:
            line = ("> " + " ".join(cells)).ljust(_WIDTH)
            return Text(line, style="bold black on green")
        t = Text("  ")
        for i, cell in enumerate(cells):
            title = _COLUMNS[i][0]
            if title == "TIPO":
                style = _KIND_STYLE.get(cell.strip(), "white")
            elif title == "TACTICA":
                style = "green" if cell.strip() == "Si" else "red"
            else:
                style = "white"
            t.append(cell, style=style)
            if i < len(cells) - 1:
                t.append(" ")
        return t

    # --- Historial (paginado, del mas nuevo al mas viejo) ---
    def _history_page(self):
        club = self._club
        history = self._history()
        if not history:
            return [Text("Todavia no se jugaron partidos.", style="grey62")], 1, 1
        pages = self._pages(len(history))
        self._hist_page = max(0, min(pages - 1, self._hist_page))
        start = self._hist_page * _PAGE_SIZE
        rows = history[start:start + _PAGE_SIZE]

        lines = [
            Text("  FECHA        RES    RIVAL", style="bold green"),
            Text("-" * _WIDTH, style="grey50"),
        ]
        for m in rows:
            rival = m.away if m.home is club else m.home
            gf = m.home_goals if m.home is club else m.away_goals
            gc = m.away_goals if m.home is club else m.home_goals
            res = "G" if gf > gc else "P" if gf < gc else "E"
            style = {"G": "green", "E": "yellow", "P": "red"}[res]
            when = m.match_date.strftime("%d-%m-%Y") if m.match_date else f"J{m.matchday}"
            t = Text(f"  {when}   ", style="grey62")
            t.append(f"{res} {gf}-{gc}".ljust(7), style=style)
            t.append(f"vs {rival.name}", style="white")
            lines.append(t)
        lines += [Text("")] * (_PAGE_SIZE - len(rows))
        return lines, self._hist_page + 1, pages

    # --- Interaccion ---
    def _move(self, delta: int) -> None:
        total = len(self._upcoming())
        if total:
            self._selected = max(0, min(total - 1, self._selected + delta))
        self._refresh_content()

    def _turn_history(self, delta: int) -> None:
        pages = self._pages(len(self._history()))
        self._hist_page = max(0, min(pages - 1, self._hist_page + delta))
        self._refresh_content()

    def _open_tactic(self) -> None:
        upcoming = self._upcoming()
        if not upcoming:
            return
        from .tactic_screen import TacticScreen

        match = upcoming[self._selected]
        self.app.push_screen(
            TacticScreen(match, self._club, on_close=self._refresh_content)
        )

    def on_content_key(self, event) -> None:
        key = event.key
        if self._active_tab == _LIGA_TAB:      # Liga: el panel maneja su teclado
            self._league_panel.handle_key(event)
        elif self._active_tab == _COPA_TAB:    # Copa: sin interaccion por ahora
            return
        elif self._active_tab == _HIST_TAB:    # Historial: solo paginas
            if key in ("left", "pageup"):
                event.stop(); self._turn_history(-1)
            elif key in ("right", "pagedown"):
                event.stop(); self._turn_history(1)
        else:                                  # Proximos: cursor + paginas
            if key == "up":
                event.stop(); self._move(-1)
            elif key == "down":
                event.stop(); self._move(1)
            elif key in ("left", "pageup"):
                event.stop(); self._move(-_PAGE_SIZE)
            elif key in ("right", "pagedown"):
                event.stop(); self._move(_PAGE_SIZE)
            elif key == "enter":
                event.stop(); self._open_tactic()
