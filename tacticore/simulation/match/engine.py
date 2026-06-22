"""Motor del partido: avanza la simulacion en pasos de tiempo fijos.

`step(dt)` ejecuta un tick determinista: todo el azar sale de un `random.Random`
sembrado, asi misma seed (+ mismos comandos, mas adelante) -> mismo partido.

En este paso (B2) todavia NO hay IA: los jugadores quedan quietos y solo la
pelota se mueve (sale del saque inicial y rueda con friccion hasta frenarse).
El movimiento de los jugadores y las decisiones llegan en B3.
"""

import math
import random

from . import ai
from .entities import Side
from .geometry import Vec2
from .state import MatchPhase, MatchState

# Paso de simulacion recomendado (segundos). El render puede ir a otro FPS y
# pedir varios steps por frame; la fisica siempre avanza con un dt fijo.
DEFAULT_DT = 1.0 / 30.0

_BALL_FRICTION = 6.0    # desaceleracion de la pelota (m/s^2)
_KICKOFF_SPEED = 8.0    # velocidad del saque inicial (m/s)


class MatchEngine:
    """Avanza un `MatchState` tick a tick de forma determinista."""

    def __init__(self, state: MatchState, rng: random.Random | None = None) -> None:
        self.state = state
        self._rng = rng or random.Random()

    def step(self, dt: float = DEFAULT_DT) -> None:
        """Avanza la simulacion `dt` segundos."""
        if self.state.phase is MatchPhase.KICKOFF:
            self._kickoff()
        self._update_ball(dt)
        self._update_players(dt)
        self.state.clock += dt

    def run(self, duration: float, dt: float = DEFAULT_DT) -> None:
        """Avanza `duration` segundos en pasos de `dt`."""
        steps = int(round(duration / dt))
        for _ in range(steps):
            self.step(dt)

    # --- Internos ---

    def _kickoff(self) -> None:
        """Saca del medio: la pelota sale en una direccion al azar (por seed)."""
        angle = self._rng.uniform(0.0, 2.0 * math.pi)
        self.state.ball.velocity = Vec2(
            math.cos(angle) * _KICKOFF_SPEED, math.sin(angle) * _KICKOFF_SPEED
        )
        self.state.phase = MatchPhase.PLAYING

    def _update_ball(self, dt: float) -> None:
        ball = self.state.ball
        speed = ball.velocity.length()
        if speed > 0.0:
            # Friccion: la pelota pierde velocidad hasta frenarse.
            new_speed = max(0.0, speed - _BALL_FRICTION * dt)
            ball.velocity = ball.velocity.normalized() * new_speed
        ball.position = ball.position + ball.velocity * dt
        # Por ahora se frena en las lineas (out-of-bounds real en B3).
        clamped = self.state.pitch.clamp(ball.position)
        if clamped != ball.position:
            ball.position = clamped
            ball.velocity = Vec2(0.0, 0.0)

    def _update_players(self, dt: float) -> None:
        state = self.state
        pitch = state.pitch
        # El mas cercano a la pelota de cada equipo la persigue (segun posiciones
        # actuales); el resto sostiene su formacion.
        chasers = {
            id(ai.team_ball_chaser(state, Side.HOME)),
            id(ai.team_ball_chaser(state, Side.AWAY)),
        }
        for mp in state.all_players():
            mp.velocity = ai.decide_velocity(mp, state, id(mp) in chasers)
            mp.position = pitch.clamp(mp.position + mp.velocity * dt)
