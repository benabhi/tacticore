"""Pantalla de avance de dia: confirma y procesa el mundo.

Al presionar Espacio en una seccion se empuja esta pantalla. Primero pregunta si se
quiere avanzar (mostrando la fecha destino y que evento de la semana se procesa); al
confirmar corre `advance_day` y vuelve a la seccion.

El avance es rapido (<~250 ms incluso con el mundo completo), asi que se procesa de
forma SINCRONA en el hilo de la UI: se pinta "Procesando..." y recien ahi se avanza.
Antes se hacia en un hilo aparte con `call_from_thread` + `pop_screen`, pero popear
la pantalla desde el propio worker producia fallas intermitentes (la ventana se
cerraba sin avanzar). Sincrono es simple y confiable.

Ademas, si el dia destino es la fecha del partido de liga del club del jugador, el
cartel lo avisa (y avisa si no hay tactica: se usara una por defecto). En ese caso
el mundo se procesa SIN resolver ese partido y se encadena a la pantalla previa
(el "versus") para jugarlo en vivo; no se puede saltar.
"""

from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Static

from ...core.rng import new_rng
from ...simulation.auto_tactic import default_tactic
from ...simulation.daily import advance_day, day_event, player_match_on
from ..format import hint
from ..widgets.progress_bar import ProgressBar
from .base_screen import BaseScreen

_DAY_ES = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]


class AdvanceDayScreen(BaseScreen):
    """Confirma el avance de un dia y procesa el mundo."""

    BINDINGS = [
        ("enter", "confirm", "Confirmar"),
        ("escape", "cancel", "Cancelar"),
    ]

    CSS = """
    #viewport { align: center middle; }
    #adv_title { width: 1fr; text-align: center; color: green; text-style: bold; }
    #adv_info { width: 1fr; text-align: center; color: white; margin-top: 1; }
    #adv_bar { margin-top: 1; }
    #adv_hint { width: 1fr; text-align: center; color: $text-muted; margin-top: 1; }
    """

    def __init__(self, on_done=None) -> None:
        super().__init__()
        self._on_done = on_done
        self._processing = False

    def compose_viewport(self) -> ComposeResult:
        from datetime import timedelta

        cur = self.app.game.calendar.current_date
        self._target = cur + timedelta(days=1)  # fecha destino = manana
        # Si manana hay partido de liga del club del jugador, se juega en vivo.
        self._match = player_match_on(self.app.game, self._target)
        yield Static("AVANZAR UN DIA", id="adv_title")
        yield Static(self._info_text(), id="adv_info")
        yield ProgressBar(width=56, id="adv_bar")
        yield Static(hint(("Enter", "confirmar"), ("Esc", "cancelar")), id="adv_hint")

    def _info_text(self) -> Text:
        info = Text(justify="center")
        info.append(f"Pasar al {self._target.strftime('%d-%m-%Y')} ", style="bold white")
        info.append(f"({_DAY_ES[self._target.weekday()]})\n", style="grey70")
        info.append(day_event(self._target), style="grey62")
        if self._match is not None:
            pc = self.app.game.player_club
            rival = self._match.away if self._match.home is pc else self._match.home
            sede = "Local" if self._match.home is pc else "Visitante"
            info.append("\n\n")
            info.append(f"Tenes un partido ({self._match.kind.value}): ",
                        style="bold green")
            info.append(f"vs {rival.name} ({sede})", style="bold white")
            if self._match.tactic is None:
                info.append("\nSin tactica: se usara una por defecto.", style="yellow")
            else:
                info.append(f"\nTactica lista ({self._match.tactic.formation}).",
                            style="grey62")
        return info

    def action_cancel(self) -> None:
        if not self._processing:
            self.app.pop_screen()

    def action_confirm(self) -> None:
        if self._processing:
            return
        self._processing = True
        # Pintar "Procesando..." y recien despues (tras el refresh) avanzar, para que
        # se vea el feedback antes del pequeno freeze del calculo.
        self.query_one("#adv_info", Static).update(
            Text("Procesando...", style="grey62", justify="center"))
        self.query_one(ProgressBar).update_progress(1, 1)
        self.query_one("#adv_hint", Static).update(Text(""))
        self.call_after_refresh(self._run)

    def _run(self) -> None:
        game = self.app.game
        # Procesa el mundo. Si hay partido del jugador, se resuelve todo MENOS ese
        # (queda pendiente para jugarlo en vivo).
        advance_day(game, new_rng(game.seed + self._target.toordinal()),
                    skip_player_match=True)
        match = player_match_on(game, game.calendar.current_date)
        if match is not None:
            from .prematch_screen import PreMatchScreen

            if match.tactic is None:  # el jugador no planteo: tactica automatica
                match.tactic = default_tactic(
                    game.player_club, new_rng(game.seed + self._target.toordinal()))
            self.app.switch_screen(PreMatchScreen(match, on_done=self._on_done))
            return
        if self._on_done is not None:
            self._on_done()
        self.app.pop_screen()
