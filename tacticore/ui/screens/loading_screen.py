"""Pantalla de carga: genera el mundo mostrando una barra de progreso.

Estilo Caves of Qud: arriba el pais que se esta generando, la barra que se llena
y, debajo, un resumen con contadores que SUBEN EN VIVO (paises, ligas, clubes,
estadios, hinchadas, presidentes, DTs, jugadores). Como todo se genera junto por
club, los contadores se derivan del avance (clubes hechos). La generacion corre
en un hilo aparte; al terminar, no avanza solo: aparece un prompt parpadeante y
el jugador pulsa Enter para seguir a "Crea tu club".
"""

import time

from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Static

from ... import config
from ...core.game import GameState
from ...core.rng import new_rng
from ...domain.country import Country
from ...domain.enums import LeagueTier
from ...generators import WorldGenerator
from ..widgets.progress_bar import ProgressBar
from .base_screen import BaseScreen
from .create_club_screen import CreateClubScreen

_PROMPT = "Presiona <ENTER> para continuar"
_VAL_W = 6   # ancho de la columna de valores (hasta "37,120")
_LBL_W = 11  # ancho de cada columna de labels (hasta "Presidentes")
# Ancho de la fila del bloque (valor + label + centro + label + valor) y el
# padding para centrarlo en los 80 de pantalla (el align del viewport no alcanza
# porque los demas widgets son 1fr).
_ROW_W = 2 * _VAL_W + 2 * _LBL_W + 7
_PAD = " " * ((config.SCREEN_WIDTH - _ROW_W) // 2)


def _ceil_div(a: int, b: int) -> int:
    return -(-a // b)


class LoadingScreen(BaseScreen):
    """Genera el mundo, muestra el avance y los contadores en vivo."""

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
        width: 1fr;
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
        self._done = 0
        self._total = 1
        yield Static("T A C T I C O R E", id="title")
        yield Static("Preparando el mundo...", id="label")
        yield ProgressBar(width=56, id="bar")
        yield Static(self._stats_text(), id="stats")
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
        self._done = done
        self._total = total
        self.query_one("#label", Static).update(label)
        self.query_one(ProgressBar).update_progress(done, total)
        self.query_one("#stats", Static).update(self._stats_text())

    def _finish(self, world: list[Country]) -> None:
        # El mundo generado pasa a ser el estado raiz; el club del jugador se
        # inserta despues, en "Crea tu club".
        self.app.game = GameState.new(
            seed=self.app.seed,
            start_date=config.SEASON_START_DATE,
            countries=world,
        )
        # Dejar los contadores en su valor final exacto.
        self._done = sum(len(lg.clubs) for co in world for lg in co.leagues)
        self._total = self._done
        self.query_one("#stats", Static).update(self._stats_text())
        self.query_one(ProgressBar).update_progress(self._done, self._done)
        self.query_one("#label", Static).update("Mundo generado.")
        # Listo: ahora se puede continuar y arranca el parpadeo del prompt.
        self._ready = True
        self.set_interval(0.5, self._toggle_blink)

    # --- Contadores derivados del avance (todo crece junto con los clubes) ---
    def _counts(self) -> list[tuple[str, int]]:
        done, total = self._done, self._total
        per_league = config.CLUBS_PER_LEAGUE
        tiers = len(LeagueTier)
        per_country = per_league * tiers
        n_countries = max(1, total // per_country)
        n_leagues = n_countries * tiers
        paises = min(n_countries, _ceil_div(done, per_country))
        ligas = min(n_leagues, _ceil_div(done, per_league))
        return [
            ("Paises", paises),
            ("Ligas", ligas),
            ("Clubes", done),
            ("Estadios", done),
            ("Hinchadas", done),
            ("Presidentes", done),
            ("DTs", done),
            ("Jugadores", done * config.SQUAD_SIZE),
        ]

    def _stats_text(self) -> Text:
        """Resumen centrado en 4 columnas: valor | label) (label | valor.

        Las dos columnas de labels se alinean hacia el centro (la izquierda a la
        derecha, la derecha a la izquierda) y los valores quedan en los extremos,
        asi el bloque se ve centrado.
        """
        stats = self._counts()
        half = len(stats) // 2
        t = Text()
        for r in range(half):
            l_label, l_value = stats[r]
            r_label, r_value = stats[r + half]
            t.append(_PAD)
            t.append(f"{l_value:,}".rjust(_VAL_W), style="bold green")
            t.append("  ")
            t.append(l_label.rjust(_LBL_W), style="grey70")
            t.append(" ")
            t.append(":", style="bold yellow")   # espina central, un toque de color
            t.append(" ")
            t.append(r_label.ljust(_LBL_W), style="grey70")
            t.append("  ")
            t.append(f"{r_value:,}".ljust(_VAL_W), style="bold green")
            t.append("\n")
        return t

    def _toggle_blink(self) -> None:
        self._blink_on = not self._blink_on
        self.query_one("#prompt", Static).update(_PROMPT if self._blink_on else "")

    def action_continue(self) -> None:
        # Solo avanza una vez que termino la generacion.
        if self._ready:
            self.app.switch_screen(CreateClubScreen())
