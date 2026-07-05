"""Pantalla previa al partido: el "versus".

Antes de que arranque el encuentro se presentan los dos clubes enfrentados: a la
IZQUIERDA el LOCAL y a la DERECHA el VISITANTE, cada uno con su emblema y su
nombre en su color de identidad, y "VS" al medio. El club del jugador se resalta
en verde. Un texto parpadeante ("Enter para continuar") invita a arrancar; con
Enter empieza el partido en vivo, que ya no se puede saltar.

Solo ASCII, 80x25 (directivas 1 y 2). El emblema (identicon) mide 12x7.
"""

from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Static

from ...core.rng import new_rng
from ...persistence import savegame
from ...simulation.auto_tactic import default_tactic
from ...simulation.daily import finish_player_match
from ...simulation.match.formation import get_formation
from ..identicon import emblem_lines, identicon_color
from .base_screen import BaseScreen

_W = 80
_MARGIN = 13     # sangria antes del emblema local (emblema = 12 de ancho)
_MID = 30        # separacion entre emblemas cuando no va el "VS"
_NAME_FIELD = 26  # ancho del campo del nombre bajo cada emblema
_BLINK_INTERVAL = 0.5


def _center(text: str, width: int) -> str:
    """Centra `text` en un campo de `width` (lo recorta si no entra)."""
    text = text[:width]
    pad = width - len(text)
    left = pad // 2
    return " " * left + text + " " * (pad - left)


class PreMatchScreen(BaseScreen):
    """El "versus" antes del partido del club del jugador."""

    CSS = """
    #viewport { align: center middle; }
    #vs { width: 80; height: 25; }
    """

    def __init__(self, match, on_done=None) -> None:
        super().__init__()
        self._match = match
        self._on_done = on_done
        self._blink = True
        self._timer = None
        self._started = False

    def compose_viewport(self) -> ComposeResult:
        yield Static(self._content_text(), id="vs")

    def on_mount(self) -> None:
        self._timer = self.set_interval(_BLINK_INTERVAL, self._toggle_blink)

    def _toggle_blink(self) -> None:
        self._blink = not self._blink
        self.query_one("#vs", Static).update(self._content_text())

    # --- Render ---
    def _player_club(self):
        game = self.app.game
        return game.player_club if game else None

    def _content_text(self) -> Text:
        m = self._match
        pc = self._player_club()
        left = emblem_lines(m.home.name)   # 7 filas x 12
        right = emblem_lines(m.away.name)

        t = Text(no_wrap=True, justify="left")
        for _ in range(3):
            t.append("\n")
        from ...domain.enums import MatchKind

        header = "PARTIDO" if m.kind is MatchKind.LEAGUE else m.kind.value.upper()
        t.append(_center(header, _W) + "\n", style="bold green")
        when = m.match_date.strftime("%d-%m-%Y") if m.match_date else "-"
        sub = f"Jornada {m.matchday}   {when}" if m.kind is MatchKind.LEAGUE else when
        t.append(_center(sub, _W) + "\n", style="grey62")
        t.append("\n")
        # Etiquetas LOCAL / VISITANTE (el equipo del jugador va en verde).
        t.append_text(self._labels_line(pc))
        t.append("\n")
        # Emblemas enfrentados (VS en la fila del medio).
        for i in range(len(left)):
            t.append_text(self._emblem_row(i, left, right))
            t.append("\n")
        # Nombres bajo cada emblema, en su color de identidad.
        t.append_text(self._names_line())
        t.append("\n\n")
        t.append_text(self._plan_line(pc))
        t.append("\n\n")
        prompt = "Enter para continuar" if self._blink else ""
        t.append(_center(prompt, _W), style="bold white")
        return t

    def _labels_line(self, pc) -> Text:
        m = self._match
        t = Text(no_wrap=True)
        t.append(" " * 6)
        home_style = "bold green" if m.home is pc else "grey50"
        away_style = "bold green" if m.away is pc else "grey50"
        t.append(_center("LOCAL", _NAME_FIELD), style=home_style)
        t.append(" " * 16)
        t.append(_center("VISITANTE", _NAME_FIELD), style=away_style)
        return t

    def _emblem_row(self, i, left, right) -> Text:
        t = Text(no_wrap=True)
        t.append(" " * _MARGIN)
        t.append_text(left[i])
        if i == len(left) // 2:
            t.append(" " * ((_MID - 2) // 2))
            t.append("VS", style="bold white")
            t.append(" " * (_MID - 2 - (_MID - 2) // 2))
        else:
            t.append(" " * _MID)
        t.append_text(right[i])
        return t

    def _names_line(self) -> Text:
        m = self._match
        t = Text(no_wrap=True)
        t.append(" " * 6)
        t.append(_center(m.home.name.upper(), _NAME_FIELD),
                 style=f"bold {identicon_color(m.home.name)}")
        t.append(" " * 16)
        t.append(_center(m.away.name.upper(), _NAME_FIELD),
                 style=f"bold {identicon_color(m.away.name)}")
        return t

    def _plan_line(self, pc) -> Text:
        """Recuerda al jugador con que formacion sale su equipo."""
        m = self._match
        tactic = m.tactic
        if tactic is None or pc is None:
            return Text("")
        return Text(_center(f"Tu equipo juega {tactic.formation}", _W),
                    style="grey62")

    # --- Teclado ---
    def on_key(self, event) -> None:
        if event.key == "enter":
            event.stop()
            self._start_match()

    def _start_match(self) -> None:
        if self._started:
            return
        self._started = True
        if self._timer is not None:
            self._timer.stop()
        from .match_screen import MatchScreen

        game = self.app.game
        m = self._match
        pc = game.player_club
        player_formation = get_formation(m.tactic.formation)
        rival = m.away if m.home is pc else m.home
        # El rival elige su formacion segun la mentalidad de SU DT (reusa la logica
        # de la tactica automatica; el resultado igual sale del motor por seed).
        rival_formation = get_formation(
            default_tactic(rival, new_rng(game.seed)).formation)
        if m.home is pc:
            home_formation, away_formation = player_formation, rival_formation
        else:
            home_formation, away_formation = rival_formation, player_formation

        seed = game.seed + game.calendar.current_date.toordinal()
        on_done = self._on_done

        def on_finish(home_goals: int, away_goals: int) -> None:
            finish_player_match(game, m, home_goals, away_goals)
            savegame.save_game(game)
            if on_done is not None:
                on_done()

        self.app.switch_screen(MatchScreen(
            m.home, m.away, seed=seed,
            home_formation=home_formation, away_formation=away_formation,
            on_finish=on_finish,
        ))
