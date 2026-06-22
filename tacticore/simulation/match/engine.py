"""Motor del partido: avanza la simulacion en pasos de tiempo fijos.

`step(dt)` ejecuta un tick determinista: todo el azar sale de un `random.Random`
sembrado, asi misma seed (+ mismos comandos, mas adelante) -> mismo partido.

B3.2: hay posesion. El jugador que alcanza la pelota la "lleva" (la pelota va
con el, un poco por delante). Mientras la tiene decide: patear al arco si esta
cerca, pasar al companero mas libre si lo presionan, o gambetear hacia el arco.
Los goles y el arquero llegan en B3.3.
"""

import math
import random

from . import ai
from .entities import Side
from .geometry import Vec2
from .state import MatchPhase, MatchState

# Paso de simulacion recomendado (segundos).
DEFAULT_DT = 1.0 / 30.0

_BALL_FRICTION = 6.0      # desaceleracion de la pelota (m/s^2)
_KICKOFF_SPEED = 8.0      # velocidad del saque inicial (m/s)
_CONTROL_RADIUS = 0.8     # a esta distancia un jugador domina la pelota (m)
_KICK_COOLDOWN = 0.4      # tras patear, nadie puede dominarla un ratito (s)
_SHOOT_RANGE = 25.0       # distancia al arco para intentar el remate (m)
_PRESSURE_RADIUS = 2.5    # si un rival esta mas cerca, el que lleva la suelta (m)
_MAX_PASS_DIST = 35.0     # alcance maximo de un pase (m)
_PASS_SPEED = 14.0        # velocidad de un pase (m/s)
_SHOOT_SPEED = 22.0       # velocidad de un remate (m/s)
_DRIBBLE_FACTOR = 0.85    # se gambetea un poco mas lento que corriendo libre
_DRIBBLE_OFFSET = 0.5     # la pelota va esta distancia por delante del que lleva


class MatchEngine:
    """Avanza un `MatchState` tick a tick de forma determinista."""

    def __init__(self, state: MatchState, rng: random.Random | None = None) -> None:
        self.state = state
        self._rng = rng or random.Random()
        self._kick_cooldown = 0.0

    def step(self, dt: float = DEFAULT_DT) -> None:
        """Avanza la simulacion `dt` segundos."""
        if self.state.phase is MatchPhase.KICKOFF:
            self._kickoff()
        self._kick_cooldown = max(0.0, self._kick_cooldown - dt)
        self._acquire_possession()
        self._move_players(dt)  # la accion del que lleva puede soltar la pelota
        self._update_ball(dt)
        self.state.clock += dt

    def run(self, duration: float, dt: float = DEFAULT_DT) -> None:
        """Avanza `duration` segundos en pasos de `dt`."""
        for _ in range(int(round(duration / dt))):
            self.step(dt)

    # --- Internos ---

    def _kickoff(self) -> None:
        """Saca del medio: la pelota sale en una direccion al azar (por seed)."""
        angle = self._rng.uniform(0.0, 2.0 * math.pi)
        self.state.ball.velocity = Vec2(
            math.cos(angle) * _KICKOFF_SPEED, math.sin(angle) * _KICKOFF_SPEED
        )
        self.state.phase = MatchPhase.PLAYING

    def _acquire_possession(self) -> None:
        """Si la pelota esta suelta, la domina el jugador mas cercano que la pise."""
        ball = self.state.ball
        if ball.owner is not None or self._kick_cooldown > 0.0:
            return
        on_ball = [
            mp
            for mp in self.state.all_players()
            if mp.position.distance_to(ball.position) <= _CONTROL_RADIUS
        ]
        if on_ball:
            ball.owner = min(
                on_ball, key=lambda mp: mp.position.distance_to(ball.position)
            )
            ball.velocity = Vec2(0.0, 0.0)

    def _move_players(self, dt: float) -> None:
        state = self.state
        pitch = state.pitch
        owner = state.ball.owner
        chasers = {
            id(ai.team_ball_chaser(state, Side.HOME)),
            id(ai.team_ball_chaser(state, Side.AWAY)),
        }
        for mp in state.all_players():
            if mp is owner:
                mp.velocity = self._owner_action(mp)
            else:
                mp.velocity = ai.decide_velocity(mp, state, id(mp) in chasers)
            mp.position = pitch.clamp(mp.position + mp.velocity * dt)

    def _owner_action(self, owner) -> Vec2:
        """Decide que hace el que tiene la pelota; devuelve su velocidad."""
        state = self.state
        goal = ai.attacking_goal(state, owner.team)

        # Cerca del arco -> remate.
        if owner.position.distance_to(goal) <= _SHOOT_RANGE:
            self._kick(owner, goal, _SHOOT_SPEED)
            return Vec2(0.0, 0.0)

        # Presionado -> pase al mejor companero (o remate si no hay).
        rival = ai.nearest_opponent(owner, state)
        if rival.position.distance_to(owner.position) < _PRESSURE_RADIUS:
            target = ai.best_pass_target(owner, state, _MAX_PASS_DIST)
            if target is not None:
                self._kick(owner, target.position, _PASS_SPEED)
            else:
                self._kick(owner, goal, _SHOOT_SPEED)
            return Vec2(0.0, 0.0)

        # Libre -> gambetea hacia el arco.
        return ai.arrive(
            owner.position, goal, ai.max_speed(owner.player) * _DRIBBLE_FACTOR
        )

    def _kick(self, kicker, target: Vec2, speed: float) -> None:
        """Patea la pelota desde `kicker` hacia `target` y la suelta."""
        ball = self.state.ball
        ball.velocity = (target - kicker.position).normalized() * speed
        ball.owner = None
        self._kick_cooldown = _KICK_COOLDOWN

    def _update_ball(self, dt: float) -> None:
        state = self.state
        ball = state.ball

        # Si alguien la lleva, la pelota va con el, un poco por delante.
        if ball.owner is not None:
            owner = ball.owner
            goal = ai.attacking_goal(state, owner.team)
            ahead = (goal - owner.position).normalized() * _DRIBBLE_OFFSET
            ball.position = state.pitch.clamp(owner.position + ahead)
            ball.velocity = owner.velocity
            return

        # Suelta: rueda con friccion hasta frenarse, acotada a la cancha.
        speed = ball.velocity.length()
        if speed > 0.0:
            new_speed = max(0.0, speed - _BALL_FRICTION * dt)
            ball.velocity = ball.velocity.normalized() * new_speed
        ball.position = ball.position + ball.velocity * dt
        clamped = state.pitch.clamp(ball.position)
        if clamped != ball.position:
            ball.position = clamped
            ball.velocity = Vec2(0.0, 0.0)
