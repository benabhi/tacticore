"""Seccion Liga: la competicion del jugador, en una sola vista.

Muestra, de arriba a abajo:
- la tabla de posiciones (con columna de MOVimiento: ^ subio, v bajo, - igual);
- el fixture de una jornada (navegable con las flechas), con el partido propio
  resaltado;
- una franja de estadisticas de liga (disciplina, lesionados, mercado).

El fixture se genera al crear/cargar la partida; aca, por las dudas, se genera si
todavia no existe.
"""

from rich.text import Text

from ...core.rng import new_rng
from ...simulation.season import Standing, compute_standings, generate_league_fixture
from .section_screen import SectionScreen

_WIDTH = 76    # ancho util de la tabla
_FORM_LEN = 5  # cuantos resultados recientes se muestran en "ULT5"

# Columnas de la tabla: (titulo, ancho, alineacion). "M" = columna de movimiento.
_FIXED = [
    ("PJ", 2, "r"), ("G", 2, "r"), ("E", 2, "r"), ("P", 2, "r"),
    ("GF", 2, "r"), ("GC", 2, "r"), ("DIF", 4, "r"), ("Pts", 3, "r"),
    ("ULT5", _FORM_LEN, "l"),
]
# Ancho del nombre = total - marcador(2) - separadores - resto de columnas fijas.
_HEAD_COLS = [("#", 2, "r"), ("M", 1, "l"), ("EQUIPO", 0, "l")] + _FIXED
_NAME_W = _WIDTH - 2 - (len(_HEAD_COLS) + 1) - sum(w for _, w, _ in _HEAD_COLS)
_COLUMNS = [("#", 2, "r"), ("M", 1, "l"), ("EQUIPO", _NAME_W, "l")] + _FIXED

# Color de cada resultado en la forma reciente (ASCII: G/E/P, "-" sin jugar).
_FORM_STYLE = {"G": "green", "E": "yellow", "P": "red", "-": "grey42"}
# Color del movimiento de posicion (^ subio / v bajo / - sin cambio).
_MOVE_STYLE = {"^": "green", "v": "red", "-": "grey42"}


class LeagueScreen(SectionScreen):
    """Posiciones, fixture y estadisticas de la liga del jugador (una vista)."""

    section_key = "L"
    section_title = "Liga"
    tabs = ("Tabla",)

    def __init__(self) -> None:
        super().__init__()
        self._round = None   # jornada mostrada en el fixture (None = auto)

    @property
    def _league(self):
        game = self.app.game
        return game.player_league if game else None

    def _ensure_fixture(self):
        game = self.app.game
        league = self._league
        if league is not None and not league.matches:
            generate_league_fixture(league, new_rng(game.seed))
        return league

    def _total_rounds(self, league) -> int:
        return max((m.matchday for m in league.matches), default=0)

    def _played_rounds(self, league) -> int:
        """Cantidad de jornadas COMPLETAS (todos sus partidos jugados)."""
        total = self._total_rounds(league)
        return sum(
            1 for r in range(1, total + 1)
            if all(m.played for m in league.matches if m.matchday == r)
        )

    def _next_round(self, league) -> int:
        for r in range(1, self._total_rounds(league) + 1):
            if any(not m.played for m in league.matches if m.matchday == r):
                return r
        return max(1, self._total_rounds(league))

    # --- Render ---
    def render_tab(self, index: int) -> Text:
        league = self._ensure_fixture()
        if league is None:
            return Text("No hay liga para mostrar.", style="white")
        # La tabla cierra con su propia linea, asi el fixture va pegado; queda una
        # linea de aire entre las estadisticas y la barra de menu inferior.
        t = Text()
        self._append_standings(t, league)
        self._append_fixture(t, league)
        t.append("\n")
        self._append_stats(t, league)
        return t

    # --- Tabla de posiciones (con movimiento) ---
    def _moves(self, league) -> dict:
        """id(club) -> '^' / 'v' / '-' comparando con la jornada anterior."""
        played = self._played_rounds(league)
        current = compute_standings(league)
        if played < 1:
            return {id(s.club): "-" for s in current}
        prev = compute_standings(league, upto_matchday=played - 1)
        prev_pos = {id(s.club): i for i, s in enumerate(prev, start=1)}
        moves = {}
        for pos, s in enumerate(current, start=1):
            before = prev_pos.get(id(s.club), pos)
            moves[id(s.club)] = "^" if before > pos else "v" if before < pos else "-"
        return moves

    def _append_standings(self, t: Text, league) -> None:
        standings = compute_standings(league)
        moves = self._moves(league)
        total = self._total_rounds(league)
        played = self._played_rounds(league)
        club = self.app.game.player_club

        t.append("POSICIONES", style="bold green")
        t.append(f"     Jornada {min(played + 1, total)}/{total}\n", style="grey62")
        self._append_header(t)
        for pos, standing in enumerate(standings, start=1):
            self._append_row(t, pos, standing, moves[id(standing.club)], club)
        t.append("-" * _WIDTH + "\n", style="grey50")

    @staticmethod
    def _fmt(text, width: int, align: str) -> str:
        text = str(text)[:width]
        return text.rjust(width) if align == "r" else text.ljust(width)

    def _append_header(self, t: Text) -> None:
        cells = [self._fmt(h, w, a) for h, w, a in _COLUMNS]
        line = ("  " + " ".join(cells)).ljust(_WIDTH)
        t.append(line + "\n", style="bold green")
        t.append("-" * _WIDTH + "\n", style="grey50")

    def _row_values(self, pos: int, move: str, s: Standing) -> list[str]:
        diff = s.goal_diff
        return [
            str(pos), move, s.club.name, str(s.played), str(s.won), str(s.drawn),
            str(s.lost), str(s.goals_for), str(s.goals_against),
            f"+{diff}" if diff > 0 else str(diff), str(s.points),
            self._form_text(s.form),
        ]

    @staticmethod
    def _form_text(form: list[str]) -> str:
        recent = form[-_FORM_LEN:]
        return "-" * (_FORM_LEN - len(recent)) + "".join(recent)

    def _append_row(self, t: Text, pos: int, s: Standing, move: str, player_club) -> None:
        values = self._row_values(pos, move, s)
        cells = [self._fmt(v, w, a) for v, (_, w, a) in zip(values, _COLUMNS)]
        if s.club is player_club:
            line = ("> " + " ".join(cells)).ljust(_WIDTH)
            t.append(line + "\n", style="bold black on green")
            return
        t.append("  ")
        for i, cell in enumerate(cells):
            title = _COLUMNS[i][0]
            if title == "ULT5":
                for ch in cell:
                    t.append(ch, style=_FORM_STYLE.get(ch, "grey42"))
            elif title == "M":
                t.append(cell, style=_MOVE_STYLE.get(cell.strip(), "grey42"))
            else:
                t.append(cell, style="white")
            if i < len(cells) - 1:
                t.append(" ")
        used = 2 + sum(len(c) for c in cells) + (len(cells) - 1)
        if used < _WIDTH:
            t.append(" " * (_WIDTH - used))
        t.append("\n")

    # --- Fixture (una jornada, navegable) ---
    def _append_fixture(self, t: Text, league) -> None:
        total = self._total_rounds(league)
        rnd = self._round if self._round is not None else self._next_round(league)
        rnd = max(1, min(total, rnd))
        club = self.app.game.player_club

        matches = [m for m in league.matches if m.matchday == rnd]
        when = ""
        if matches and matches[0].match_date:
            when = "  -  " + matches[0].match_date.strftime("%d-%m-%Y")
        t.append(f"FIXTURE  Jornada {rnd}/{total}{when}", style="bold green")
        t.append("     (flechas: cambiar jornada)\n", style="grey62")
        for m in matches:
            mine = m.home is club or m.away is club
            score = f"{m.home_goals} - {m.away_goals}" if m.played else "  vs "
            line = f"  {m.home.name:>28.28}  {score:^7}  {m.away.name:<28.28}"
            t.append(line + "\n", style="bold white" if mine else "white")

    # --- Franja de estadisticas de liga ---
    def _append_stats(self, t: Text, league) -> None:
        injured = sum(
            1 for club in league.clubs for p in club.players if p.is_injured
        )
        t.append("ESTADISTICAS DE LIGA\n", style="bold green")
        # Disciplina y mercado: 0 hasta que existan el motor de partido y el mercado.
        parts = [
            ("Rojas", 0), ("Amarillas", 0), ("Lesionados", injured),
            ("Fichajes", 0), ("Compras", 0), ("Ventas", 0),
        ]
        t.append("  ")
        for i, (label, value) in enumerate(parts):
            t.append(f"{label}: ", style="grey62")
            t.append(str(value), style="white")
            if i < len(parts) - 1:
                t.append("   ")
        t.append("\n")

    # --- Navegacion del fixture ---
    def on_content_key(self, event) -> None:
        league = self._league
        if league is None:
            return
        total = self._total_rounds(league)
        current = self._round if self._round is not None else self._next_round(league)
        key = event.key
        if key in ("left", "up", "pageup"):
            event.stop(); self._round = max(1, current - 1); self._refresh_content()
        elif key in ("right", "down", "pagedown"):
            event.stop(); self._round = min(total, current + 1); self._refresh_content()
