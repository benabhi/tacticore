"""Seccion Liga: la tabla de posiciones de la liga del jugador.

Por ahora solo muestra la tabla (PJ, G, E, P, GF, GC, diferencia, puntos y la
forma de los ultimos partidos). El club del jugador va resaltado. El fixture de
la temporada se genera al crear/cargar la partida; aca, por las dudas, se genera
si todavia no existe.
"""

from collections.abc import Iterator

from rich.text import Text
from textual.widget import Widget
from textual.widgets import Static

from ...core.rng import new_rng
from ...simulation.season import Standing, compute_standings, generate_league_fixture
from .section_screen import SectionScreen

_WIDTH = 76   # ancho util del contenido (80 menos el padding 1 2)
_FORM_LEN = 5  # cuantos resultados recientes se muestran en "ULT5"

# Columnas de la tabla: (titulo, ancho, alineacion). EQUIPO se estira para llenar.
_FIXED = [
    ("#", 2, "r"), ("PJ", 2, "r"), ("G", 2, "r"), ("E", 2, "r"), ("P", 2, "r"),
    ("GF", 2, "r"), ("GC", 2, "r"), ("DIF", 4, "r"), ("Pts", 3, "r"),
    ("ULT5", _FORM_LEN, "l"),
]
# El nombre llena lo que sobra: total - marcador(2) - separadores - columnas fijas.
_NAME_W = _WIDTH - 2 - (len(_FIXED) + 1) - sum(w for _, w, _ in _FIXED)
_COLUMNS = [("#", 2, "r"), ("EQUIPO", _NAME_W, "l")] + _FIXED[1:]

# Color de cada resultado en la forma reciente (ASCII: G/E/P, "-" sin jugar).
_FORM_STYLE = {"G": "green", "E": "yellow", "P": "red", "-": "grey42"}


class LeagueScreen(SectionScreen):
    """Tabla de posiciones de la liga del jugador."""

    section_key = "L"

    CSS = """
    #content {
        padding: 1 2;
    }
    """

    def content(self) -> Iterator[Widget]:
        yield Static(self._table_text(), id="standings")

    @property
    def _league(self):
        game = self.app.game
        return game.player_league if game else None

    def _table_text(self) -> Text:
        game = self.app.game
        league = self._league
        if league is None:
            return Text("No hay liga para mostrar.", style="white")
        # Red de seguridad: si por algun camino no se genero el fixture, generarlo.
        if not league.matches:
            generate_league_fixture(league, new_rng(game.seed))

        standings = compute_standings(league)
        total_rounds = max((m.matchday for m in league.matches), default=0)
        played_rounds = sum(
            1
            for r in range(1, total_rounds + 1)
            if all(m.played for m in league.matches if m.matchday == r)
        )

        t = Text()
        t.append(f"TABLA DE POSICIONES  -  {league.name}\n", style="bold green")
        t.append(f"Jornada {min(played_rounds + 1, total_rounds)}/{total_rounds}\n\n",
                 style="grey62")
        self._append_header(t)
        for pos, standing in enumerate(standings, start=1):
            self._append_row(t, pos, standing, game.player_club)
        return t

    @staticmethod
    def _fmt(text, width: int, align: str) -> str:
        text = str(text)[:width]
        return text.rjust(width) if align == "r" else text.ljust(width)

    def _append_header(self, t: Text) -> None:
        cells = [self._fmt(h, w, a) for h, w, a in _COLUMNS]
        line = ("  " + " ".join(cells)).ljust(_WIDTH)
        t.append(line + "\n", style="bold green")
        t.append("-" * _WIDTH + "\n", style="grey50")

    def _row_values(self, pos: int, s: Standing) -> list[str]:
        diff = s.goal_diff
        return [
            str(pos),
            s.club.name,
            str(s.played),
            str(s.won),
            str(s.drawn),
            str(s.lost),
            str(s.goals_for),
            str(s.goals_against),
            f"+{diff}" if diff > 0 else str(diff),
            str(s.points),
            self._form_text(s.form),
        ]

    @staticmethod
    def _form_text(form: list[str]) -> str:
        """Ultimos resultados como 5 caracteres (rellena con '-' lo no jugado)."""
        recent = form[-_FORM_LEN:]
        return "-" * (_FORM_LEN - len(recent)) + "".join(recent)

    def _append_row(self, t: Text, pos: int, s: Standing, player_club) -> None:
        values = self._row_values(pos, s)
        cells = [self._fmt(v, w, a) for v, (_, w, a) in zip(values, _COLUMNS)]
        is_player = s.club is player_club

        if is_player:
            # Fila del club del jugador: barra resaltada de ancho completo.
            line = ("> " + " ".join(cells)).ljust(_WIDTH)
            t.append(line + "\n", style="bold black on green")
            return

        t.append("  ")
        for i, cell in enumerate(cells):
            if _COLUMNS[i][0] == "ULT5":
                self._append_form_cell(t, cell)
            else:
                t.append(cell, style="white")
            if i < len(cells) - 1:
                t.append(" ")
        used = 2 + sum(len(c) for c in cells) + (len(cells) - 1)
        if used < _WIDTH:
            t.append(" " * (_WIDTH - used))
        t.append("\n")

    @staticmethod
    def _append_form_cell(t: Text, cell: str) -> None:
        """Pinta cada caracter de la forma reciente segun el resultado."""
        for ch in cell:
            t.append(ch, style=_FORM_STYLE.get(ch, "grey42"))
