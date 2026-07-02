"""Pantalla de carga: genera el mundo con una barra centrada.

Minimalista: el titulo, una linea que dice QUE se esta generando (el pais en
curso) y una barra de progreso, todo centrado en pantalla. La generacion corre
en un hilo aparte; al terminar no avanza solo: aparece un prompt parpadeante y el
jugador pulsa Enter para seguir a "Crea tu club".
"""

import time

from textual.app import ComposeResult
from textual.widgets import Static

from ... import config
from ...core.game import GameState
from ...core.rng import new_rng
from ...domain.country import Country
from ...generators import WorldGenerator
from ..widgets.progress_bar import ProgressBar
from .base_screen import BaseScreen
from .create_club_screen import CreateClubScreen

_PROMPT = "Presiona <ENTER> para continuar"


class LoadingScreen(BaseScreen):
    """Genera el mundo mostrando una barra centrada y el paso en curso."""

    BINDINGS = [("enter", "continue", "Continuar")]

    CSS = """
    #viewport {
        align: center middle;
    }
    #title {
        width: 1fr;
        text-align: center;
        color: green;
        text-style: bold;
    }
    #label {
        width: 1fr;
        text-align: center;
        color: white;
        margin-top: 1;
    }
    #bar {
        margin-top: 1;
    }
    #prompt {
        width: 1fr;
        text-align: center;
        color: yellow;
        text-style: bold;
        margin-top: 1;
    }
    """

    def compose_viewport(self) -> ComposeResult:
        yield Static("T A C T I C O R E", id="title")
        yield Static("Preparando el mundo...", id="label")
        yield ProgressBar(width=56, id="bar")
        yield Static("", id="prompt")

    def on_mount(self) -> None:
        self._last_pct = -1
        self._ready = False
        self._blink_on = True
        # Genera en un hilo para no bloquear la UI.
        self.run_worker(self._generate, thread=True, exclusive=True)

    # --- Worker (corre en un hilo aparte) ---
    def _generate(self) -> None:
        seed = self.app.seed
        world = WorldGenerator(new_rng(seed)).generate(progress=self._on_progress)
        self.app.call_from_thread(self._finish, world)

    def _on_progress(self, label: str, done: int, total: int) -> None:
        # Solo refresca la UI cuando cambia el porcentaje entero (evita saturar).
        pct = round(done * 100 / total)
        if pct != self._last_pct:
            self._last_pct = pct
            self.app.call_from_thread(self._update_ui, label, done, total)
            if config.LOADING_STEP_DELAY:
                time.sleep(config.LOADING_STEP_DELAY)

    # --- Estos corren en el hilo de la UI (via call_from_thread) ---
    def _update_ui(self, label: str, done: int, total: int) -> None:
        self.query_one("#label", Static).update(label)
        self.query_one(ProgressBar).update_progress(done, total)

    def _finish(self, world: list[Country]) -> None:
        # El mundo generado pasa a ser el estado raiz; el club del jugador se
        # inserta despues, en "Crea tu club".
        self.app.game = GameState.new(
            seed=self.app.seed,
            start_date=config.SEASON_START_DATE,
            countries=world,
        )
        total = sum(len(lg.clubs) for co in world for lg in co.leagues)
        self.query_one(ProgressBar).update_progress(total, total)
        self.query_one("#label", Static).update("Mundo generado.")
        # Listo: ahora se puede continuar y arranca el parpadeo del prompt.
        self._ready = True
        self.set_interval(0.5, self._toggle_blink)

    def _toggle_blink(self) -> None:
        self._blink_on = not self._blink_on
        self.query_one("#prompt", Static).update(_PROMPT if self._blink_on else "")

    def action_continue(self) -> None:
        # Solo avanza una vez que termino la generacion.
        if self._ready:
            self.app.switch_screen(CreateClubScreen())
