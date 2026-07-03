"""Pantalla de avance de dia: confirma y luego procesa el mundo con una barra.

Al presionar Espacio en una seccion se empuja esta pantalla. Primero pregunta si
se quiere avanzar (mostrando la fecha destino y que evento de la semana se va a
procesar); al confirmar, corre `advance_day` en un hilo aparte con una barra de
progreso centrada (el "pasar un dia" calcula cosas de TODOS los clubes). Al
terminar, vuelve a la seccion (pop_screen).
"""

import time

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
    """Confirma el avance de un dia y procesa el mundo con barra de progreso."""

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
        game = self.app.game
        cur = game.calendar.current_date
        # Fecha destino = manana; el evento depende de su dia de la semana.
        from datetime import timedelta

        target = cur + timedelta(days=1)
        self._target = target
        yield Static("AVANZAR UN DIA", id="adv_title")
        info = Text(justify="center")
        info.append(f"Pasar al {target.strftime('%d-%m-%Y')} ", style="bold white")
        info.append(f"({_DAY_ES[target.weekday()]})\n", style="grey70")
        info.append(day_event(target), style="grey62")
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
        # El feedback "Procesando..." se muestra al recibir el primer progreso.
        self.run_worker(self._process, thread=True, exclusive=True)

    # --- Worker: corre advance_day en un hilo ---
    def _process(self) -> None:
        game = self.app.game
        rng = new_rng(game.seed + self._target.toordinal())
        advance_day(game, rng, progress=self._on_progress)
        self.app.call_from_thread(self._finish)

    def _on_progress(self, label: str, done: int, total: int) -> None:
        self.app.call_from_thread(self._update_bar, label, done, total)
        if total > 1:
            time.sleep(0.002)  # apenas para que la barra se vea avanzar

    def _update_bar(self, label: str, done: int, total: int) -> None:
        self.query_one(ProgressBar).update_progress(done, total)
        self.query_one("#adv_info", Static).update(
            Text(label, style="white", justify="center")
        )
        self.query_one("#adv_hint", Static).update(
            Text("Procesando...", style="grey62", justify="center")
        )

    def _finish(self) -> None:
        if self._on_done is not None:
            self._on_done()
        self.app.pop_screen()
