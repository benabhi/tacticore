"""Pantalla del partido en tiempo real (version minima, C8 en progreso).

Corre el `MatchEngine` con un temporizador y refresca la cancha en cada frame:
se ven los 22 numeros y la pelota moverse. Arriba, un HUD con marcador y reloj.
Por ahora: pausa (ESPACIO) y salir (Q). Faltan velocidad x2/x4 y los controles
del manager (cambios, zonas, eventos), que llegan en el resto de la Fase C.
"""

from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Static

from ...core.rng import new_rng
from ...domain.club import Club
from ...simulation.match import MatchEngine, MatchPhase, Side, kickoff_state
from ...simulation.match.narration import narrate_segments
from ..palette import AWAY, HOME, MUTED
from ..widgets.pitch import MatchPitch
from .base_screen import BaseScreen

# Ritmo de juego del demo.
_FRAME_INTERVAL = 0.05   # segundos reales por frame (20 fps)
_STEPS_PER_FRAME = 1     # ticks de simulacion por frame (~0.67x tiempo real)
_FULL_TIME = 600.0       # duracion del partido en segundos simulados


class MatchScreen(BaseScreen):
    """Mira un partido entre dos clubes corriendo el motor en vivo."""

    BINDINGS = [
        ("space", "toggle_pause", "Pausa"),
        ("q", "leave", "Salir"),
    ]

    CSS = """
    #hud {
        height: 1;
        background: black;
        color: white;
        text-style: bold;
    }
    MatchPitch {
        height: 1fr;
    }
    #log {
        height: 1;
        background: black;
        color: white;
    }
    """

    def __init__(self, home: Club, away: Club, seed: int = 0, **kwargs) -> None:
        super().__init__(**kwargs)
        self._home = home
        self._away = away
        self._seed = seed
        self._paused = False
        self._timer = None
        self._log_shown = 0  # cuantos eventos del relato ya mostramos

    def compose_viewport(self) -> ComposeResult:
        yield Static("", id="hud")
        yield MatchPitch(id="pitch")
        yield Static("", id="log")

    def on_mount(self) -> None:
        state = kickoff_state(self._home, self._away)
        self._engine = MatchEngine(state, new_rng(self._seed))
        self.query_one("#pitch", MatchPitch).state = state
        self._update_hud()
        self._timer = self.set_interval(_FRAME_INTERVAL, self._tick)

    def _tick(self) -> None:
        if self._paused:
            return
        state = self._engine.state
        if state.clock >= _FULL_TIME:
            state.phase = MatchPhase.FINISHED
            if self._timer is not None:
                self._timer.stop()
            self._update_hud()
            return
        for _ in range(_STEPS_PER_FRAME):
            self._engine.step()
        self.query_one("#pitch", MatchPitch).refresh()
        self._update_hud()
        self._update_commentary()

    def _update_commentary(self) -> None:
        """Muestra el relato del ultimo evento nuevo en la linea de abajo."""
        log = self._engine.state.log
        if len(log) > self._log_shown:
            self.query_one("#log", Static).update(self._commentary(log[-1]))
            self._log_shown = len(log)

    def _commentary(self, event) -> Text:
        """Arma la linea: reloj en gris + frase con los nombres en color de equipo."""
        mm, ss = int(event.clock // 60), int(event.clock % 60)
        color = None if event.team is None else (HOME if event.team is Side.HOME else AWAY)
        text = Text(no_wrap=True, overflow="ellipsis")
        text.append(f"{mm:02d}:{ss:02d} ", style=MUTED)
        for chunk, is_name in narrate_segments(event):
            text.append(chunk, style=f"bold {color}" if (is_name and color) else "")
        return text

    def _update_hud(self) -> None:
        state = self._engine.state
        clock = min(state.clock, _FULL_TIME)
        mm, ss = int(clock // 60), int(clock % 60)
        if state.phase is MatchPhase.FINISHED:
            tag = "  FINAL"
        elif self._paused:
            tag = "  PAUSA"
        else:
            tag = ""
        event = f"  {state.last_event}" if state.last_event else ""
        hud = (
            f" {self._home.short_name} {state.score_home} - "
            f"{state.score_away} {self._away.short_name}"
            f"    {mm:02d}:{ss:02d}{tag}{event}"
            f"    [ESPACIO] pausa  [Q] salir"
        )
        self.query_one("#hud", Static).update(hud)

    def action_toggle_pause(self) -> None:
        self._paused = not self._paused
        self._update_hud()

    def action_leave(self) -> None:
        self.app.exit()
