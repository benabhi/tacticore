"""Motor del partido: avanza la simulacion en pasos de tiempo fijos.

`step(dt)` ejecuta un tick determinista: todo el azar sale de un `random.Random`
sembrado, y las ordenes del manager entran por una cola de comandos sellados con
su tick. Asi misma seed + mismos comandos -> mismo partido (replay). El motor no
distingue si los comandos los puso la UI en vivo o un partido grabado.

B3.2: hay posesion. El jugador que alcanza la pelota la "lleva" (la pelota va
con el, un poco por delante). Mientras la tiene decide: patear al arco si esta
cerca, pasar al companero mas libre si lo presionan, o gambetear hacia el arco.

B3.3: hay goles. Si la pelota cruza la linea de arco entre los palos se anota,
se suma al marcador y se vuelve a sacar del medio. El arquero ataja dentro de su
area (mas alcance) y, cuando domina, despeja en vez de gambetear.
"""

import math
import random

from . import ai
from .commands import Command
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
_PRESSURE_RADIUS = 1.6    # si un rival esta mas cerca, el que lleva la suelta (m)
_MAX_PASS_DIST = 35.0     # alcance maximo de un pase (m)
_PASS_SPEED = 14.0        # velocidad de un pase (m/s)
_SHOOT_SPEED = 25.0       # velocidad de un remate (m/s)
_DRIBBLE_FACTOR = 0.85    # se gambetea un poco mas lento que corriendo libre
_DRIBBLE_OFFSET = 0.5     # la pelota va esta distancia por delante del que lleva
_GK_REACH = 1.7           # el arquero domina la pelota a este radio dentro del area (m)
_CLEAR_SPEED = 24.0       # velocidad del despeje del arquero (m/s)
_GOAL_KICK_DEPTH = 5.5    # el saque de arco sale desde el borde del area chica (m)
_RESTART_NUDGE = 0.4      # la pelota del saque queda esta distancia adentro del limite


def _other(side: Side) -> Side:
    """El equipo contrario."""
    return Side.HOME if side is Side.AWAY else Side.AWAY


def _nudge_inside(coord: float, maximum: float) -> float:
    """Lleva una coordenada del borde (0 o maximum) a un pelin adentro del campo."""
    return _RESTART_NUDGE if coord <= 0.0 else maximum - _RESTART_NUDGE


class MatchEngine:
    """Avanza un `MatchState` tick a tick de forma determinista."""

    def __init__(
        self,
        state: MatchState,
        rng: random.Random | None = None,
        commands: list[Command] | None = None,
    ) -> None:
        self.state = state
        self._rng = rng or random.Random()
        self._kick_cooldown = 0.0
        self._tick = 0
        # Si hay un saque pendiente (lateral/corner/saque de arco), solo este
        # equipo puede tomar la pelota hasta que la ponga en juego.
        self._restart_side: Side | None = None
        # Comandos pendientes agrupados por el tick en que se aplican.
        self._pending: dict[int, list[Command]] = {}
        # Registro de todo lo programado (para grabar/reproducir el partido).
        self.command_log: list[Command] = []
        for cmd in commands or ():
            self._enqueue(cmd)

    def schedule(self, command: Command) -> None:
        """Programa un comando del manager (en vivo). No puede ser en el pasado."""
        if command.tick < self._tick:
            raise ValueError(
                f"comando para el tick {command.tick} pero el partido va por {self._tick}"
            )
        self._enqueue(command)

    def _enqueue(self, command: Command) -> None:
        self._pending.setdefault(command.tick, []).append(command)
        self.command_log.append(command)

    def step(self, dt: float = DEFAULT_DT) -> None:
        """Avanza la simulacion `dt` segundos."""
        # Comandos del manager de este tick (mismo camino en vivo y en replay).
        for command in self._pending.pop(self._tick, ()):
            command.apply(self.state)
        if self.state.phase is MatchPhase.KICKOFF:
            self._kickoff()
        self._kick_cooldown = max(0.0, self._kick_cooldown - dt)
        self._acquire_possession()
        self._move_players(dt)  # la accion del que lleva puede soltar la pelota
        self._update_ball(dt)
        self._move_referee(dt)
        self.state.clock += dt
        self._tick += 1

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
        """Si la pelota esta suelta, la domina el jugador mas cercano que la alcance.

        Cada jugador tiene su radio de control; el arquero llega mas lejos
        (atajada) cuando esta dentro de su area.
        """
        ball = self.state.ball
        if ball.owner is not None or self._kick_cooldown > 0.0:
            return
        # Con un saque pendiente, solo el equipo que saca puede tomarla.
        candidates = self.state.all_players()
        if self._restart_side is not None:
            candidates = [mp for mp in candidates if mp.team is self._restart_side]
        on_ball = [
            mp
            for mp in candidates
            if mp.position.distance_to(ball.position) <= self._reach(mp)
        ]
        if on_ball:
            owner = min(on_ball, key=lambda mp: mp.position.distance_to(ball.position))
            ball.owner = owner
            ball.velocity = Vec2(0.0, 0.0)
            self.state.last_touch = owner.team
            self._restart_side = None  # pelota en juego de nuevo

    def _reach(self, mp) -> float:
        """Radio (m) al que un jugador domina la pelota; mayor para el arquero en su area."""
        if ai.is_goalkeeper(mp):
            own_area = self.state.pitch.penalty_area(mp.team is Side.HOME)
            if own_area.contains(mp.position):
                return _GK_REACH
        return _CONTROL_RADIUS

    def _move_referee(self, dt: float) -> None:
        """El arbitro trota siguiendo la jugada, sin tocar la pelota."""
        ref = self.state.referee
        ref.velocity = ai.referee_velocity(ref, self.state)
        ref.position = self.state.pitch.clamp(ref.position + ref.velocity * dt)

    def _move_players(self, dt: float) -> None:
        state = self.state
        owner = state.ball.owner
        if owner is None:
            self._move_loose_ball(dt)
        else:
            self._move_with_owner(dt, owner)

    def _move_loose_ball(self, dt: float) -> None:
        """Pelota suelta: cada equipo manda a su mas cercano; el resto sostiene."""
        state = self.state
        pitch = state.pitch
        chasers = {
            id(ai.team_ball_chaser(state, Side.HOME)),
            id(ai.team_ball_chaser(state, Side.AWAY)),
        }
        for mp in state.all_players():
            if ai.is_goalkeeper(mp):
                mp.velocity = ai.goalkeeper_velocity(mp, state)
            else:
                mp.velocity = ai.decide_velocity(mp, state, id(mp) in chasers)
            mp.position = pitch.clamp(mp.position + mp.velocity * dt)

    def _move_with_owner(self, dt: float, owner) -> None:
        """Hay dueno: un equipo ataca; el otro presiona la pelota y marca."""
        state = self.state
        pitch = state.pitch
        defending = _other(owner.team)
        presser = ai.team_ball_chaser(state, defending)
        for mp in state.all_players():
            if mp is owner:
                mp.velocity = self._owner_action(mp)
            elif ai.is_goalkeeper(mp):
                mp.velocity = ai.goalkeeper_velocity(mp, state)
            elif mp.team is defending:
                # Uno presiona la pelota; el resto marca su zona/rival.
                if mp is presser:
                    mp.velocity = ai.decide_velocity(mp, state, is_chaser=True)
                else:
                    mp.velocity = ai.marking_velocity(mp, state)
            else:
                # Companero del que tiene la pelota: por ahora sostiene posicion.
                mp.velocity = ai.decide_velocity(mp, state, is_chaser=False)
            mp.position = pitch.clamp(mp.position + mp.velocity * dt)

    def _owner_action(self, owner) -> Vec2:
        """Decide que hace el que tiene la pelota; devuelve su velocidad."""
        state = self.state
        goal = ai.attacking_goal(state, owner.team)

        # Arquero -> despeja: busca un companero adelante o revienta hacia el arco.
        if ai.is_goalkeeper(owner):
            target = ai.best_pass_target(owner, state, _MAX_PASS_DIST * 2.0)
            if target is not None:
                self._kick(owner, target.position, _CLEAR_SPEED)
            else:
                self._kick(owner, goal, _CLEAR_SPEED)
            return Vec2(0.0, 0.0)

        # Cerca del arco -> remate apuntado a un palo.
        if owner.position.distance_to(goal) <= _SHOOT_RANGE:
            self._shoot(owner, goal)
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

    def _shoot(self, owner, goal: Vec2) -> None:
        """Remata al arco apuntando al palo mas lejos del arquero, con error.

        Mejor `shooting` -> apunta mas al palo y con menos dispersion (mas dificil
        de atajar). El error puede mandarla afuera: es un remate desviado.
        """
        pitch = self.state.pitch
        half = pitch.goal_width / 2
        rival_side = Side.AWAY if owner.team is Side.HOME else Side.HOME
        keeper = ai.team_goalkeeper(self.state, rival_side)
        # Apunta al palo contrario al lado donde esta parado el arquero.
        if keeper is not None and keeper.position.y >= goal.y:
            aim_side = -1.0
        else:
            aim_side = 1.0
        accuracy = owner.player.shooting / 100.0
        target_y = goal.y + aim_side * half * (0.4 + 0.6 * accuracy)
        target_y += self._rng.uniform(-1.0, 1.0) * (1.0 - accuracy) * half * 1.5
        self._kick(owner, Vec2(goal.x, target_y), _SHOOT_SPEED)

    def _kick(self, kicker, target: Vec2, speed: float) -> None:
        """Patea la pelota desde `kicker` hacia `target` y la suelta."""
        ball = self.state.ball
        ball.velocity = (target - kicker.position).normalized() * speed
        ball.owner = None
        self.state.last_touch = kicker.team
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
        new_pos = ball.position + ball.velocity * dt

        # Gol? cruzo la linea de arco entre los palos (antes de acotar a la cancha).
        scorer = self._goal_scored(new_pos)
        if scorer is not None:
            self._score(scorer)
            return

        clamped = state.pitch.clamp(new_pos)
        if clamped != new_pos:
            # Salio del campo: lateral, corner o saque de arco.
            self._restart_out_of_play(new_pos)
        else:
            ball.position = new_pos

    def _restart_out_of_play(self, out_pos: Vec2) -> None:
        """La pelota salio: decide el saque (lateral/corner/saque de arco)."""
        state = self.state
        pitch = state.pitch
        last = state.last_touch

        if out_pos.x < 0.0 or out_pos.x > pitch.length:
            # Salio por la linea de fondo: corner o saque de arco.
            end_x = 0.0 if out_pos.x < 0.0 else pitch.length
            defending = Side.HOME if end_x == 0.0 else Side.AWAY
            if last is defending:
                # La toco por ultimo el que defiende -> corner del atacante.
                corner_y = 0.0 if out_pos.y < pitch.width / 2 else pitch.width
                spot = Vec2(
                    _nudge_inside(end_x, pitch.length),
                    _nudge_inside(corner_y, pitch.width),
                )
                restart_side = _other(defending)
                event = "Corner"
            else:
                # La toco el atacante -> saque de arco del que defiende.
                gx = _GOAL_KICK_DEPTH if end_x == 0.0 else pitch.length - _GOAL_KICK_DEPTH
                spot = Vec2(gx, pitch.width / 2)
                restart_side = defending
                event = "Saque de arco"
        else:
            # Salio por la linea de banda: lateral del rival del ultimo toque.
            side_y = 0.0 if out_pos.y < pitch.width / 2 else pitch.width
            x = min(max(out_pos.x, 0.0), pitch.length)
            spot = Vec2(x, _nudge_inside(side_y, pitch.width))
            restart_side = _other(last) if last is not None else Side.HOME
            event = "Lateral"

        ball = state.ball
        ball.position = spot
        ball.velocity = Vec2(0.0, 0.0)
        ball.owner = None
        self._restart_side = restart_side
        state.last_event = event

    def _goal_scored(self, point: Vec2) -> Side | None:
        """Equipo que anota si `point` cruzo una linea de arco entre los palos."""
        pitch = self.state.pitch
        if not pitch.is_in_goal_mouth(point.y):
            return None
        if point.x <= 0.0:
            return Side.AWAY  # el visitante ataca el arco home (x = 0)
        if point.x >= pitch.length:
            return Side.HOME  # el local ataca el arco away (x = length)
        return None

    def _score(self, side: Side) -> None:
        """Suma el gol al marcador y prepara el saque del medio."""
        if side is Side.HOME:
            self.state.score_home += 1
        else:
            self.state.score_away += 1
        self.state.last_event = "Gol"
        self._reset_for_kickoff()

    def _reset_for_kickoff(self) -> None:
        """Vuelve a todos a su formacion y la pelota al centro, listo para sacar."""
        state = self.state
        for mp in state.all_players():
            mp.position = mp.base_position
            mp.velocity = Vec2(0.0, 0.0)
        ball = state.ball
        ball.owner = None
        ball.position = state.pitch.center
        ball.velocity = Vec2(0.0, 0.0)
        self._kick_cooldown = 0.0
        self._restart_side = None
        state.phase = MatchPhase.KICKOFF
