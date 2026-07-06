"""Panel de Liga: la competicion en una vista navegable, embebida en Partidos.

Antes era una seccion propia (Liga); ahora vive como la pestaña "Liga" de la
seccion Partidos. Es un panel (no una pantalla): lo instancia la pantalla
anfitriona (`MatchesScreen`), que le pide el contenido (`render`) y le pasa el
teclado (`handle_key`) cuando su pestaña esta activa. Muestra, de arriba a abajo:

- la tabla de posiciones de la division actual (con columna de MOVimiento:
  ^ subio, v bajo, - igual), con un cursor para elegir equipo;
- el fixture de una jornada (navegable), con el partido propio resaltado;
- una franja de estadisticas de liga (disciplina, lesionados, mercado).

Teclas: arriba/abajo eligen equipo (cursor); izquierda/derecha cambian de division
(los 5 niveles A-E del pais); [ y ] cambian la jornada del fixture; n elige pais;
Esc resetea la vista; Enter (mas adelante) abrira la info del equipo seleccionado.
"""

from rich.text import Text

from ... import config
from ...core.rng import new_rng
from ...domain.enums import LeagueTier
from ...simulation.season import Standing, compute_standings, generate_league_fixture
from ..format import hint
from ..palette import TAG, TIER

_WIDTH = config.SCREEN_WIDTH  # la tabla ocupa TODO el ancho (80)
_FORM_LEN = 5  # cuantos resultados recientes se muestran en "ULT5"
_LEFT_W = 46   # ancho de la columna izquierda (fixture) en la zona de dos columnas
_TIER_ORDER = list(LeagueTier)  # A, B, C, D, E (orden de calidad)

# Columnas de la tabla: (titulo, ancho, alineacion). "M" = columna de movimiento.
# ULT5 (ultima) va a la derecha para pegarse al borde y llenar el ancho.
_FIXED = [
    ("PJ", 2, "r"), ("G", 2, "r"), ("E", 2, "r"), ("P", 2, "r"),
    ("GF", 2, "r"), ("GC", 2, "r"), ("DIF", 4, "r"), ("Pts", 3, "r"),
    ("ULT5", _FORM_LEN, "r"),
]
# Ancho del nombre = total - marcador(2) - separadores(cols-1) - resto de columnas.
_HEAD_COLS = [("#", 2, "r"), ("M", 1, "l"), ("EQUIPO", 0, "l")] + _FIXED
_NAME_W = _WIDTH - 2 - (len(_HEAD_COLS) - 1) - sum(w for _, w, _ in _HEAD_COLS)
_COLUMNS = [("#", 2, "r"), ("M", 1, "l"), ("EQUIPO", _NAME_W, "l")] + _FIXED

# Color de cada resultado en la forma reciente (ASCII: G/E/P, "-" sin jugar).
_FORM_STYLE = {"G": "green", "E": "yellow", "P": "red", "-": "grey42"}
# Color del movimiento de posicion (^ subio / v bajo / - sin cambio).
_MOVE_STYLE = {"^": "green", "v": "red", "-": "grey42"}


def _goal_style(a: int, b: int) -> str:
    """Verde si `a` gana, rojo si pierde, blanco si empatan."""
    if a > b:
        return "bold green"
    if a < b:
        return "bold red"
    return "white"


class LeaguePanel:
    """Posiciones (ciclables por division), fixture y stats de la liga."""

    def __init__(self, host) -> None:
        self._host = host     # pantalla anfitriona (MatchesScreen): da app y refresh
        self._country = None   # pais mostrado (None = el del jugador)
        self._division = None  # indice de la division mostrada (None = la del jugador)
        self._selected = 0     # equipo seleccionado en la tabla (cursor)
        self._round = None     # jornada mostrada en el fixture (None = auto)

    @property
    def app(self):
        return self._host.app

    def _refresh(self) -> None:
        self._host._refresh_content()

    # --- Pais y divisiones ---
    def _current_country(self):
        game = self.app.game
        return self._country or (game.player_country if game else None)

    def _divisions(self) -> list:
        country = self._current_country()
        if country is None:
            return []
        return sorted(country.leagues, key=lambda lg: _TIER_ORDER.index(lg.tier))

    def _current_league(self):
        divs = self._divisions()
        if not divs:
            return self.app.game.player_league if self.app.game else None
        if self._division is None:  # arranca en la division del jugador
            pl = self.app.game.player_league
            self._division = next((i for i, lg in enumerate(divs) if lg is pl), 0)
        self._division %= len(divs)
        return divs[self._division]

    def _ensure_fixture(self, league):
        # El fixture de la liga vista se genera on-demand (idempotente). La liga
        # del jugador ya viene generada; cada liga usa una semilla propia por tier.
        if league is not None and not league.matches:
            seed = self.app.game.seed + _TIER_ORDER.index(league.tier)
            generate_league_fixture(league, new_rng(seed))
        return league

    def _total_rounds(self, league) -> int:
        return max((m.matchday for m in league.matches), default=0)

    def _played_rounds(self, league) -> int:
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
    def render(self) -> Text:
        league = self._ensure_fixture(self._current_league())
        if league is None:
            return Text("No hay liga para mostrar.", style="white")
        self._selected = max(0, min(len(league.clubs) - 1, self._selected))
        t = Text()
        self._append_standings(t, league)
        self._append_fixture(t, league)
        self._append_stats(t, league)
        return t

    # --- Tabla de posiciones (cursor + tu equipo) ---
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
        club = self.app.game.player_club

        country = self._current_country()
        code = country.code if country else "-"
        # Una sola linea: titulo con el CODIGO de pais + la division + los atajos
        # (compactos: flechas como ^v y <>) -> entra todo en 80 columnas.
        t.append("POSICIONES  ", style="bold green")
        t.append(code, style=f"bold {TAG}")  # codigo de pais, mismo cian del selector
        t.append(" - Liga ", style="bold white")
        t.append(league.tier.value, style=f"bold {TIER}")  # division (varia): lila
        t.append("   ", style="bold white")
        t.append("(", style="grey62")
        t.append_text(hint(("^v", "equipo"), ("<>", "liga"), ("Enter", "info"),
                           ("n", "pais"), ("Esc", "reset"), sep=" "))
        t.append(")\n", style="grey62")
        self._append_header(t)
        for pos, standing in enumerate(standings, start=1):
            is_cursor = (pos - 1) == self._selected
            self._append_row(t, pos, standing, moves[id(standing.club)], club, is_cursor)
        t.append("-" * _WIDTH + "\n", style="grey50")  # cierra la tabla antes del fixture

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

    def _append_row(self, t, pos, s, move, player_club, is_cursor) -> None:
        values = self._row_values(pos, move, s)
        cells = [self._fmt(v, w, a) for v, (_, w, a) in zip(values, _COLUMNS)]
        # Prioridad: cursor (barra verde) > tu equipo (blanco brillante) > normal.
        if is_cursor:
            line = ("> " + " ".join(cells)).ljust(_WIDTH)
            t.append(line + "\n", style="bold black on green")
            return
        if s.club is player_club:
            line = ("  " + " ".join(cells)).ljust(_WIDTH)
            t.append(line + "\n", style="bold white")
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

    # --- Fixture (dos columnas: la jornada + snapshot de tu equipo) ---
    def _append_fixture(self, t: Text, league) -> None:
        left = self._fixture_lines(league)
        right = self._team_snapshot_lines()
        for i in range(max(len(left), len(right))):
            lline = left[i] if i < len(left) else Text("")
            rline = right[i] if i < len(right) else Text("")
            t.append_text(lline)
            t.append(" " * max(2, _LEFT_W - len(lline.plain) + 2))
            t.append_text(rline)
            t.append("\n")

    def _fixture_lines(self, league) -> list[Text]:
        total = self._total_rounds(league)
        rnd = self._round if self._round is not None else self._next_round(league)
        rnd = max(1, min(total, rnd))
        club = self.app.game.player_club

        matches = [m for m in league.matches if m.matchday == rnd]
        when = matches[0].match_date.strftime("%d-%m") if (matches and matches[0].match_date) else ""
        head = Text()
        head.append(f"FIXTURE  J.{rnd}/{total}  {when}  ", style="bold green")
        head.append("(", style="grey62")
        head.append_text(hint(("[ ]", "jornada")))
        head.append(")", style="grey62")
        lines = [head]
        for m in matches:
            lines.append(self._match_line(m, club))
        return lines

    def _match_line(self, m, club) -> Text:
        """Una fila del fixture: 'local   G vs G   visitante' con goles coloreados.

        Sin jugar, los goles son un '_' gris; jugado, el que va ganando en verde y
        el que pierde en rojo (empate en blanco). Tres espacios a cada lado del vs.
        """
        mine = m.home is club or m.away is club
        name_style = "bold white" if mine else "white"
        t = Text()
        t.append(f"{m.home.name:>18.18} ", style=name_style)
        if m.played:
            gh, ga = m.home_goals, m.away_goals
            t.append(str(gh), style=_goal_style(gh, ga))
            t.append(" vs ", style="grey62")
            t.append(str(ga), style=_goal_style(ga, gh))
        else:
            t.append("_", style="grey50")
            t.append(" vs ", style="grey62")
            t.append("_", style="grey50")
        t.append(f" {m.away.name:<18.18}", style=name_style)
        return t

    def _team_snapshot_lines(self) -> list[Text]:
        # Snapshot de TU equipo (independiente de la division que estes mirando):
        # partido anterior con resultado y proximo partido con la prevision del clima.
        from ...simulation.weather import forecast

        game = self.app.game
        pl = game.player_league
        club = game.player_club
        mine = sorted(
            (m for m in pl.matches if m.home is club or m.away is club),
            key=lambda m: m.matchday,
        ) if pl else []
        prev = next((m for m in reversed(mine) if m.played), None)
        nxt = next((m for m in mine if not m.played), None)

        lines = [Text("PARTIDO ANTERIOR", style="bold green")]
        if prev is None:
            lines.append(Text("  sin jugar aun", style="grey62"))
        else:
            rival = prev.away if prev.home is club else prev.home
            gf = prev.home_goals if prev.home is club else prev.away_goals
            gc = prev.away_goals if prev.home is club else prev.home_goals
            res = "G" if gf > gc else "P" if gf < gc else "E"
            lines.append(Text(f"  vs {rival.name:.14}  {gf}-{gc} {res}", style="white"))

        lines.append(Text("PARTIDO PROXIMO", style="bold green"))
        if nxt is None:
            lines.append(Text("  -", style="grey62"))
        else:
            rival = nxt.away if nxt.home is club else nxt.home
            sede = "Local" if nxt.home is club else "Visita"
            lines.append(Text(f"  vs {rival.name:.14} ({sede})", style="bold white"))
            lines.append(Text(f"  Clima: {forecast(nxt, game.seed)}", style="grey70"))
        return lines

    # --- Franja de estadisticas de liga ---
    def _append_stats(self, t: Text, league) -> None:
        injured = sum(1 for cl in league.clubs for p in cl.players if p.is_injured)
        t.append("ESTADISTICAS DE LIGA", style="bold green")
        season = self.app.game.season if self.app.game else 1
        t.append(f"   Temporada {season}\n", style="grey70")
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

    # --- Teclado ---
    def _change_round(self, delta: int) -> None:
        league = self._current_league()
        total = self._total_rounds(league)
        current = self._round if self._round is not None else self._next_round(league)
        self._round = max(1, min(total, current + delta))
        self._refresh()

    def _change_division(self, delta: int) -> None:
        divs = self._divisions()
        if not divs:
            return
        self._current_league()  # asegura que _division este inicializado
        self._division = (self._division + delta) % len(divs)
        self._round = None
        self._selected = 0
        self._refresh()

    def _open_country_picker(self) -> None:
        from .country_select_screen import CountrySelectScreen

        game = self.app.game
        available = [(c.name, c.code) for c in game.countries]
        self.app.push_screen(
            CountrySelectScreen(available, title="ELEGI UN PAIS"),
            self._on_country_picked,
        )

    def _on_country_picked(self, choice) -> None:
        if choice is None:  # cancelo la seleccion
            return
        _, code = choice
        game = self.app.game
        country = next((c for c in game.countries if c.code == code), None)
        if country is None:
            return
        # Cambia de pais manteniendo la division (mismo tier); resetea cursor y jornada.
        self._country = country
        self._selected = 0
        self._round = None
        self._refresh()

    def handle_key(self, event) -> None:
        league = self._current_league()
        if league is None:
            return
        key, ch = event.key, event.character
        if key == "up":
            event.stop(); self._selected = max(0, self._selected - 1); self._refresh()
        elif key == "down":
            n = len(league.clubs)
            event.stop(); self._selected = min(n - 1, self._selected + 1); self._refresh()
        elif key == "left":
            event.stop(); self._change_division(-1)
        elif key == "right":
            event.stop(); self._change_division(1)
        elif key == "n":
            event.stop(); self._open_country_picker()
        elif key == "enter":
            event.stop()  # reservado: ver info del equipo seleccionado (proximamente)
        elif key == "escape":
            event.stop(); self._reset_view()
        elif ch == "[":
            event.stop(); self._change_round(-1)
        elif ch == "]":
            event.stop(); self._change_round(1)

    def _reset_view(self) -> None:
        """Vuelve la vista a lo por defecto: tu pais, tu division, jornada actual."""
        self._country = None
        self._division = None
        self._selected = 0
        self._round = None
        self._refresh()
