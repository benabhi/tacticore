"""Seccion Liga: la competicion del jugador.

Pestañas:
- Tabla: la tabla de posiciones (PJ, G, E, P, GF, GC, DIF, Pts, ULT5).
- Fixture: el calendario de la temporada, una jornada por vez (navegable con las
  flechas), resaltando los partidos del club del jugador.

El fixture se genera al crear/cargar la partida; aca, por las dudas, se genera si
todavia no existe.
"""

from rich.text import Text

from ...core.rng import new_rng
from ...simulation.season import Standing, compute_standings, generate_league_fixture
from .section_screen import SectionScreen

_WIDTH = 76   # ancho util de la tabla
_FORM_LEN = 5  # cuantos resultados recientes se muestran en "ULT5"

# Columnas de la tabla de posiciones: (titulo, ancho, alineacion).
_FIXED = [
    ("#", 2, "r"), ("PJ", 2, "r"), ("G", 2, "r"), ("E", 2, "r"), ("P", 2, "r"),
    ("GF", 2, "r"), ("GC", 2, "r"), ("DIF", 4, "r"), ("Pts", 3, "r"),
    ("ULT5", _FORM_LEN, "l"),
]
_NAME_W = _WIDTH - 2 - (len(_FIXED) + 1) - sum(w for _, w, _ in _FIXED)
_COLUMNS = [("#", 2, "r"), ("EQUIPO", _NAME_W, "l")] + _FIXED[1:]

# Color de cada resultado en la forma reciente (ASCII: G/E/P, "-" sin jugar).
_FORM_STYLE = {"G": "green", "E": "yellow", "P": "red", "-": "grey42"}


class LeagueScreen(SectionScreen):
    """Tabla de posiciones y fixture de la liga del jugador."""

    section_key = "L"
    section_title = "Liga"
    tabs = ("Tabla", "Fixture")

    def __init__(self) -> None:
        super().__init__()
        self._round = None   # jornada mostrada en la pestaña Fixture (None = auto)

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

    def _next_round(self, league) -> int:
        """Primera jornada con algun partido sin jugar (o la ultima)."""
        for r in range(1, self._total_rounds(league) + 1):
            if any(not m.played for m in league.matches if m.matchday == r):
                return r
        return max(1, self._total_rounds(league))

    # --- Render por pestaña ---
    def render_tab(self, index: int) -> Text:
        league = self._ensure_fixture()
        if league is None:
            return Text("No hay liga para mostrar.", style="white")
        if index == 1:
            return self._fixture_text(league)
        return self._standings_text(league)

    # --- Tabla de posiciones ---
    def _standings_text(self, league) -> Text:
        standings = compute_standings(league)
        total = self._total_rounds(league)
        played = sum(
            1 for r in range(1, total + 1)
            if all(m.played for m in league.matches if m.matchday == r)
        )
        t = Text()
        t.append(f"Jornada {min(played + 1, total)}/{total}\n", style="grey62")
        self._append_header(t)
        for pos, standing in enumerate(standings, start=1):
            self._append_row(t, pos, standing, self.app.game.player_club)
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
            str(pos), s.club.name, str(s.played), str(s.won), str(s.drawn),
            str(s.lost), str(s.goals_for), str(s.goals_against),
            f"+{diff}" if diff > 0 else str(diff), str(s.points),
            self._form_text(s.form),
        ]

    @staticmethod
    def _form_text(form: list[str]) -> str:
        recent = form[-_FORM_LEN:]
        return "-" * (_FORM_LEN - len(recent)) + "".join(recent)

    def _append_row(self, t: Text, pos: int, s: Standing, player_club) -> None:
        values = self._row_values(pos, s)
        cells = [self._fmt(v, w, a) for v, (_, w, a) in zip(values, _COLUMNS)]
        if s.club is player_club:
            line = ("> " + " ".join(cells)).ljust(_WIDTH)
            t.append(line + "\n", style="bold black on green")
            return
        t.append("  ")
        for i, cell in enumerate(cells):
            if _COLUMNS[i][0] == "ULT5":
                for ch in cell:
                    t.append(ch, style=_FORM_STYLE.get(ch, "grey42"))
            else:
                t.append(cell, style="white")
            if i < len(cells) - 1:
                t.append(" ")
        used = 2 + sum(len(c) for c in cells) + (len(cells) - 1)
        if used < _WIDTH:
            t.append(" " * (_WIDTH - used))
        t.append("\n")

    # --- Fixture (una jornada por vez) ---
    def _fixture_text(self, league) -> Text:
        total = self._total_rounds(league)
        rnd = self._round if self._round is not None else self._next_round(league)
        rnd = max(1, min(total, rnd))
        club = self.app.game.player_club

        t = Text()
        t.append(f"Jornada {rnd}/{total}", style="bold green")
        t.append("    (flechas: cambiar jornada)\n\n", style="grey62")
        for m in [m for m in league.matches if m.matchday == rnd]:
            mine = m.home is club or m.away is club
            if m.played:
                score = f"{m.home_goals} - {m.away_goals}"
            else:
                score = "  vs "
            line = f"  {m.home.name:>28.28}  {score:^7}  {m.away.name:<28.28}"
            t.append(line + "\n", style="bold white" if mine else "white")
        return t

    def on_content_key(self, event) -> None:
        if self._active_tab != 1:
            return
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
