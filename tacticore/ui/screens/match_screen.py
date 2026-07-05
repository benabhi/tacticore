"""Pantalla del partido en tiempo real.

Corre el `MatchEngine` con un temporizador y refresca la cancha en cada frame:
se ven los 22 numeros y la pelota moverse. Arriba, un HUD con marcador, reloj y
velocidad; abajo, el relato del ultimo evento.

Dos modos, segun se pase `on_finish`:

- Modo DEMO (sin `on_finish`, ej. `scripts/watch_match.py`): Q sale de la app.
- Modo JUEGO (con `on_finish`): es el partido del club del jugador dentro del
  flujo. NO se puede saltar: Q no hace nada; cuando termina, con Enter se
  confirma el resultado (via `on_finish`) y se vuelve a la seccion.

En ambos: ESPACIO pausa y +/- cambian la velocidad (x1 .. x16). La velocidad es
cuantos ticks de simulacion se avanzan por frame; no altera el resultado (mismo
seed -> mismo partido), solo lo rapido que se ve.
"""

from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Static

from ...core.rng import new_rng
from ...domain.club import Club
from ...simulation.match import MatchEngine, MatchPhase, Side, kickoff_state
from ...simulation.match.narration import narrate_segments
from ..format import hint
from ..palette import AWAY, HOME, MUTED
from ..widgets.pitch import MatchPitch
from .base_screen import BaseScreen

# Ritmo de juego.
_FRAME_INTERVAL = 0.05   # segundos reales por frame (20 fps)
_SPEEDS = (1, 2, 4, 8, 16)  # ticks de simulacion por frame (multiplicador de velocidad)
_FULL_TIME = 600.0       # futbol simulado (calibrado para totales realistas por partido)
# El RELOJ del partido corre mas rapido que la animacion: esos 600 s de juego se
# muestran como 90 minutos (los dos tiempos), para que el reloj llegue a 90:00.
_MATCH_SECONDS = 90 * 60
_CLOCK_SCALE = _MATCH_SECONDS / _FULL_TIME


class MatchScreen(BaseScreen):
    """Mira un partido entre dos clubes corriendo el motor en vivo."""

    BINDINGS = [
        ("space", "toggle_pause", "Pausa"),
        ("plus", "faster", "Mas rapido"),
        ("equals_sign", "faster", "Mas rapido"),
        ("minus", "slower", "Mas lento"),
        ("enter", "advance", "Continuar"),
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

    def __init__(self, home: Club, away: Club, seed: int = 0,
                 home_formation=None, away_formation=None, on_finish=None,
                 start_speed=None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._home = home
        self._away = away
        self._seed = seed
        self._home_formation = home_formation
        self._away_formation = away_formation
        self._on_finish = on_finish   # callback(home_goals, away_goals) en modo juego
        self._paused = False
        self._finished = False
        self._timer = None
        self._log_shown = 0  # cuantos eventos del relato ya mostramos
        # En modo juego arranca acelerado (un partido completo a x1 seria largo);
        # el modo demo respeta el ritmo calibrado de watch_match (x1).
        default_speed = 4 if on_finish is not None else 1
        speed = start_speed if start_speed is not None else default_speed
        self._speed_idx = _SPEEDS.index(speed) if speed in _SPEEDS else 0

    def compose_viewport(self) -> ComposeResult:
        yield Static("", id="hud")
        yield MatchPitch(id="pitch")
        yield Static("", id="log")

    def on_mount(self) -> None:
        state = kickoff_state(
            self._home, self._away,
            home_formation=self._home_formation,
            away_formation=self._away_formation,
        )
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
            self._finished = True
            if self._timer is not None:
                self._timer.stop()
            self._update_hud()
            return
        for _ in range(_SPEEDS[self._speed_idx]):
            self._engine.step()
            if state.clock >= _FULL_TIME:
                break
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
        clock = event.clock * _CLOCK_SCALE  # reloj de partido (90 min), no el de simulacion
        mm, ss = int(clock // 60), int(clock % 60)
        color = None if event.team is None else (HOME if event.team is Side.HOME else AWAY)
        text = Text(no_wrap=True, overflow="ellipsis")
        text.append(f"{mm:02d}:{ss:02d} ", style=MUTED)
        for chunk, is_name in narrate_segments(event):
            text.append(chunk, style=f"bold {color}" if (is_name and color) else "")
        return text

    def _update_hud(self) -> None:
        state = self._engine.state
        clock = min(state.clock, _FULL_TIME) * _CLOCK_SCALE  # reloj de partido (hasta 90:00)
        mm, ss = int(clock // 60), int(clock % 60)
        speed = f"  x{_SPEEDS[self._speed_idx]}"
        if state.phase is MatchPhase.FINISHED:
            tag = "  FINAL"
        elif self._paused:
            tag = "  PAUSA"
        else:
            tag = ""
        event = f"  {state.last_event}" if state.last_event else ""
        # Ayuda de teclas segun el modo (juego = no se puede salir; demo = Q sale).
        if self._on_finish is not None:
            keys = " [Enter] continuar" if self._finished else "  [ESP] pausa  [+/-] velocidad"
        else:
            keys = "  [ESP] pausa  [+/-] velocidad  [Q] salir"
        hud = (
            f" {self._home.short_name} {state.score_home} - "
            f"{state.score_away} {self._away.short_name}"
            f"    {mm:02d}:{ss:02d}{speed}{tag}{event}"
            f"    {keys}"
        )
        self.query_one("#hud", Static).update(hud)

    def action_toggle_pause(self) -> None:
        if self._finished:
            return
        self._paused = not self._paused
        self._update_hud()

    def action_faster(self) -> None:
        self._speed_idx = min(self._speed_idx + 1, len(_SPEEDS) - 1)
        self._update_hud()

    def action_slower(self) -> None:
        self._speed_idx = max(self._speed_idx - 1, 0)
        self._update_hud()

    def action_advance(self) -> None:
        """En modo juego, tras el final Enter confirma el resultado y vuelve."""
        if self._on_finish is None or not self._finished:
            return
        state = self._engine.state
        home_goals, away_goals = state.score_home, state.score_away
        on_finish = self._on_finish
        self.app.pop_screen()
        on_finish(home_goals, away_goals)

    def action_leave(self) -> None:
        # Modo demo: Q sale de la app. Modo juego: el partido no se puede saltar.
        if self._on_finish is None:
            self.app.exit()
