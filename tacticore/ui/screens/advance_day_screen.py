"""Pantalla de avance de dia: confirma y procesa el mundo.

Al presionar Espacio en una seccion se empuja esta pantalla. Primero pregunta si se
quiere avanzar (mostrando la fecha destino y que evento de la semana se procesa); al
confirmar corre `advance_day` y vuelve a la seccion.

El avance es rapido (<~250 ms incluso con el mundo completo), asi que se procesa de
forma SINCRONA en el hilo de la UI: se pinta "Procesando..." y recien ahi se avanza.
Antes se hacia en un hilo aparte con `call_from_thread` + `pop_screen`, pero popear
la pantalla desde el propio worker producia fallas intermitentes (la ventana se
cerraba sin avanzar). Sincrono es simple y confiable.
"""

from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Static

from ...core.rng import new_rng
from ...simulation.daily import advance_day, day_event
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
        yield Static("AVANZAR UN DIA", id="adv_title")
        info = Text(justify="center")
        info.append(f"Pasar al {self._target.strftime('%d-%m-%Y')} ", style="bold white")
        info.append(f"({_DAY_ES[self._target.weekday()]})\n", style="grey70")
        info.append(day_event(self._target), style="grey62")
        yield Static(info, id="adv_info")
        yield ProgressBar(width=56, id="adv_bar")
        yield Static(hint(("Enter", "confirmar"), ("Esc", "cancelar")), id="adv_hint")

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
        advance_day(game, new_rng(game.seed + self._target.toordinal()))
        if self._on_done is not None:
            self._on_done()
        self.app.pop_screen()
