"""Pantalla de carga: genera el mundo mostrando una barra de progreso.

Estilo Caves of Qud: un texto que cuenta que se esta generando y una barra que
se llena. La generacion corre en un hilo aparte (worker) para no congelar la
UI; al terminar, pasa a la pantalla de nuevo juego.
"""

import time

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Static

from ... import config
from ...core.rng import new_rng
from ...domain.country import Country
from ...generators import WorldGenerator
from ..widgets.progress_bar import ProgressBar
from .new_game_screen import NewGameScreen


class LoadingScreen(Screen):
    """Genera el mundo y muestra el avance."""

    CSS = """
    LoadingScreen {
        align: center middle;
        background: black;
    }
    #box {
        width: 64;
        height: auto;
    }
    #title {
        text-align: center;
        color: green;
        text-style: bold;
    }
    #label {
        text-align: center;
        color: white;
        padding: 1 0;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Static("T A C T I C O R E", id="title")
            yield Static("Preparando el mundo...", id="label")
            yield ProgressBar(width=56, id="bar")

    def on_mount(self) -> None:
        self._last_pct = -1
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
        self.app.world = world
        self.app.switch_screen(NewGameScreen())
