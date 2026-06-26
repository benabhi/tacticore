"""Pantalla de carga: genera el mundo mostrando una barra de progreso.

Estilo Caves of Qud: un texto que cuenta que se esta generando y una barra que
se llena. La generacion corre en un hilo aparte (worker) para no congelar la UI.
Al terminar, NO avanza solo: revela un resumen de lo generado (en dos columnas) y
muestra un prompt parpadeante; el jugador lee las estadisticas y pulsa Enter para
seguir a "Crea tu club".
"""

import time

from rich.text import Text
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
_COL_W = 36           # ancho de cada columna del resumen
_REVEAL_STEP = 0.12   # segundos entre cada item del resumen que aparece


class LoadingScreen(BaseScreen):
    """Genera el mundo, muestra el avance y un resumen final."""

    BINDINGS = [("enter", "continue", "Continuar")]

    CSS = """
    #viewport {
        align: center top;
    }
    #title {
        width: 1fr;
        text-align: center;
        color: green;
        text-style: bold;
        margin-top: 1;
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
    #stats {
        width: 72;
        height: 8;
        margin-top: 2;
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
        yield Static("", id="stats")
        yield Static("", id="prompt")

    def on_mount(self) -> None:
        self._last_pct = -1
        self._stats: list[tuple[str, int]] = []
        self._revealed = 0
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
        self.query_one("#label", Static).update("Mundo generado.")
        self._stats = self._compute_stats(world)
        # Revela el resumen item por item, como un checklist que se va llenando.
        self._reveal_timer = self.set_interval(_REVEAL_STEP, self._reveal_step)

    def _compute_stats(self, world: list[Country]) -> list[tuple[str, int]]:
        clubs = [cl for co in world for lg in co.leagues for cl in lg.clubs]
        n_clubs = len(clubs)
        n_players = sum(len(cl.players) for cl in clubs)
        n_leagues = sum(len(co.leagues) for co in world)
        return [
            ("Paises", len(world)),
            ("Ligas", n_leagues),
            ("Clubes", n_clubs),
            ("Estadios", n_clubs),
            ("Hinchadas", n_clubs),
            ("Presidentes", n_clubs),
            ("Directores tecnicos", n_clubs),
            ("Jugadores", n_players),
        ]

    def _reveal_step(self) -> None:
        self._revealed += 1
        self.query_one("#stats", Static).update(self._stats_text())
        if self._revealed >= len(self._stats):
            self._reveal_timer.stop()
            # Listo: ahora se puede continuar y arranca el parpadeo del prompt.
            self._ready = True
            self.set_interval(0.5, self._toggle_blink)

    def _stats_text(self) -> Text:
        """Resumen en dos columnas (izquierda se llena primero, luego derecha)."""
        rows = (len(self._stats) + 1) // 2
        t = Text()
        for r in range(rows):
            for idx in (r, r + rows):
                t.append_text(self._cell(idx))
            t.append("\n")
        return t

    def _cell(self, idx: int) -> Text:
        """Una celda del resumen (vacia si todavia no se revelo, para no mover nada)."""
        if idx >= len(self._stats) or idx >= self._revealed:
            return Text(" " * _COL_W)
        label, value = self._stats[idx]
        prefix = f"  {label}: "
        number = f"{value:,}"
        cell = Text()
        cell.append(prefix, style="grey70")
        cell.append(number, style="bold green")
        pad = _COL_W - len(prefix) - len(number)
        if pad > 0:
            cell.append(" " * pad)
        return cell

    def _toggle_blink(self) -> None:
        self._blink_on = not self._blink_on
        self.query_one("#prompt", Static).update(_PROMPT if self._blink_on else "")

    def action_continue(self) -> None:
        # Solo avanza una vez que termino la generacion y el resumen.
        if self._ready:
            self.app.switch_screen(CreateClubScreen())
