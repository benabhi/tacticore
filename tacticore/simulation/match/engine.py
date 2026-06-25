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
from .entities import Role, Side
from .events import MatchEvent
from .geometry import Vec2
from .state import MatchPhase, MatchState

# Paso de simulacion recomendado (segundos).
DEFAULT_DT = 1.0 / 30.0

_BALL_FRICTION = 6.0      # desaceleracion de la pelota (m/s^2)
_KICKOFF_SPEED = 8.0      # velocidad del saque inicial (m/s)
_CONTROL_RADIUS = 0.8     # a esta distancia un jugador domina la pelota (m)
_KICK_COOLDOWN = 0.4      # tras patear, nadie puede dominarla un ratito (s)
_PRESSURE_RADIUS = 1.6    # si un rival esta mas cerca, el que lleva la suelta (m)
_CLEAR_PRESSURE = 6.0     # defensor en su area con un rival a menos de esto: despeja
_MAX_PASS_DIST = 35.0     # alcance maximo de un pase (m)
_PASS_SPEED = 14.0        # velocidad de un pase corto (m/s)
_LONG_PASS_SPEED = 19.0   # velocidad de un pase largo (m/s)
_SHORT_PASS_ERROR = 3.0   # desvio maximo de un pase corto con passing=0 (m)
_LONG_PASS_ERROR = 8.0    # desvio maximo de un pase largo con passing=0 (m)
_SHOOT_SPEED = 25.0       # velocidad de un remate (m/s)
_FREE_KICK_SHOOT_RANGE = 24.0  # desde mas cerca que esto, el tiro libre va al arco
_SAVE_BASE = 0.50         # ancla: nivel de atajadas de la liga (los atributos ajustan)
_DRIBBLE_FACTOR = 0.85    # se gambetea un poco mas lento que corriendo libre
_DRIBBLE_OFFSET = 0.5     # la pelota va esta distancia por delante del que lleva
_GK_REACH = 1.7           # el arquero domina la pelota a este radio dentro del area (m)
_CLEAR_SPEED = 24.0       # velocidad del despeje del arquero (m/s)
_GK_SHORT_SAFE = 24.0     # solo saca corto si el rival mas cercano esta a mas que esto (m)
_GK_CARRY_TIME = 2.5      # el arquero camina el area buscando opcion antes de distribuir (s)
_GK_CARRY_PRESSURE = 8.0  # si un rival se acerca mas que esto, distribuye ya (no camina)
_TAKER_FREEZE = 0.7       # el ejecutante de un saque queda quieto este rato tras jugarla (s)
_THROW_WAIT_MAX = 3.0     # el que saca el lateral espera hasta esto a tener un pase (s)
_THROW_PRESSURE = 6.0     # si un rival se acerca mas que esto al que saca, saca ya (m)
_THROW_OPTION_RANGE = 16.0  # distancia a la que un companero ya es opcion de saque (m)
_WIDE_MARGIN = 18.0       # a menos de esto de una banda, el jugador esta "abierto"
_CROSS_ZONE = 0.09        # hay que llegar BIEN al fondo (cerca de la linea) para centrar
_CROSS_SPEED = 18.0       # velocidad del centro al area (m/s)
_CROSS_FLIGHT_TIME = 3.0  # ventana del centro/rebote (gente al area, definicion dificil)
_CORNER_WAIT_MAX = 7.0    # espera de armado del corner (la gente trota al area)
_CORNER_BOX_READY = 4     # con esta cantidad de companeros en el area, ya saca el corner
_WING_SEEK_CHANCE = 0.05  # prob. por tick de abrir el juego a un extremo libre
_RECEPTION_TIME = 1.6     # tras un saque, el que recibe va a buscar la pelota este rato (s)
_SUPPORT_RUN_TIME = 1.2   # tras un pase corto, el que paso pica de apoyo este rato (s)
_GOAL_KICK_DEPTH = 5.5    # el saque de arco sale desde el borde del area chica (m)
_RESTART_NUDGE = 0.4      # la pelota del saque queda esta distancia adentro del limite
_SHOT_SAVE_SPEED = 16.0   # a mas velocidad que esto, la pelota que llega al arquero es "remate"
_PARRY_SPEED = 10.0       # velocidad del rebote cuando el arquero no la retiene (m/s)
_TACKLE_RADIUS = 1.5      # un defensor a esta distancia del que lleva intenta el quite (m)
_TACKLE_COOLDOWN = 0.6    # tras un intento de quite, espera este rato (s)
_FOUL_RECOVER = 1.0       # tras una falta, no se vuelve a quitar por este rato (s)
_HANDBALL_SPEED = 8.0      # solo una pelota mas rapida que esto puede ser "mano"
_HANDBALL_CHANCE = 0.0005  # mano: extremadamente rara (rareza, ~1 cada muchos partidos)
# Pausa (s) de "pelota muerta": la pelota se acomoda y los jugadores se
# reposicionan antes de reanudar (que el balon parado se vea y no sea instantaneo).
_SETTLE_RESTART = 1.8      # lateral / corner / saque de arco / falta / tiro libre
_SETTLE_FREEKICK = 2.8     # tiro libre / penal: mas tiempo (el ejecutante va, se arma la barrera)
_SETTLE_KICKOFF = 2.5      # saque del medio (inicio y tras gol)
_SETTLE_SAVE = 1.5         # el arquero atajo y acomoda antes de distribuir
_WALL_DIST = 9.15          # distancia (m) de la barrera al balon en un tiro libre
_WALL_MIN = 16.0           # hay barrera si el tiro libre esta entre estas distancias
_WALL_MAX = 32.0           #   del arco (mas cerca seria penal; mas lejos, sin barrera)


def _other(side: Side) -> Side:
    """El equipo contrario."""
    return Side.HOME if side is Side.AWAY else Side.AWAY


def _nudge_inside(coord: float, maximum: float) -> float:
    """Lleva una coordenada del borde (0 o maximum) a un pelin adentro del campo."""
    return _RESTART_NUDGE if coord <= 0.0 else maximum - _RESTART_NUDGE


def _clamp(value: float, low: float, high: float) -> float:
    """Acota un valor al rango [low, high]."""
    return min(max(value, low), high)


def _recovery_freeze(attr_a: float, attr_b: float) -> float:
    """Tiempo (s) que un jugador queda frenado tras perder un duelo (gambeteado o
    despojado). Mejor agilidad/reaccion -> se recupera mas rapido."""
    recovery = (attr_a + attr_b) / 2.0
    return _clamp(1.2 - recovery / 110.0, 0.4, 1.2)


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
        self._tackle_cooldown = 0.0
        self._restart_timer = 0.0  # pausa de pelota muerta en curso (s)
        self._gk_carry_timer = 0.0  # el arquero camina el area antes de distribuir (s)
        self._restart_kind: str | None = None  # tipo de saque pendiente (lateral, corner, ...)
        self._restart_taker = None  # quien va a ejecutar el saque (hasta que la juega)
        self._kickoff_side = Side.HOME  # quien saca del medio (el local al inicio)
        # Tras un saque/pase de saque: el receptor va a buscar la pelota y el que
        # la jugo NO la persigue (evita que vuelvan a su zona o que la siga el mismo).
        self._reception_id: int | None = None
        self._reception_passer_id: int | None = None
        self._reception_timer = 0.0
        # El que dio un pase corto pica de apoyo (pared / te paso y voy).
        self._support_runner_id: int | None = None
        self._support_run_timer = 0.0
        # Centro en el aire: el equipo que centro mantiene gente en el area y la
        # defensa marca, durante una ventana corta hasta que se resuelve.
        self._crossing_side: Side | None = None
        self._cross_flight_timer = 0.0
        # Corner: tiempo que lleva armandose (pelota muerta hasta que el area se llena).
        self._corner_setup = 0.0
        # Jugadores "congelados" un instante (ejecuto un saque, lo gambetearon, o
        # le quitaron la pelota): id -> tiempo restante (s). No se mueven.
        self._frozen: dict[int, float] = {}
        self._throw_wait_timer = 0.0  # el que saca el lateral espera ayuda
        self._last_kicker = None  # ultimo que pateo (para nombrar al autor del gol)
        self._tick = 0
        # Si hay un saque pendiente (lateral/corner/saque de arco/tiro libre),
        # solo este equipo puede tomar la pelota hasta que la ponga en juego.
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
        # Pelota muerta: pausa para acomodar la pelota y reposicionar a todos.
        if self._restart_timer > 0.0:
            self._restart_timer = max(0.0, self._restart_timer - dt)
            self._settle(dt)
            # Corner: sigue siendo pelota muerta (no se la roban) hasta que el area
            # se llena o se agota la espera; recien ahi se ejecuta.
            if self._restart_kind == "corner" and self._restart_side is not None:
                self._corner_setup += dt
                ready = self._box_attackers(self._restart_side) >= _CORNER_BOX_READY
                if ready or self._corner_setup >= _CORNER_WAIT_MAX:
                    self._execute_corner()
                else:
                    self._restart_timer = max(self._restart_timer, 0.1)  # mantiene la pausa
            self.state.clock += dt
            self._tick += 1
            return
        if self.state.phase is MatchPhase.KICKOFF:
            self._kickoff()
        self._kick_cooldown = max(0.0, self._kick_cooldown - dt)
        self._tackle_cooldown = max(0.0, self._tackle_cooldown - dt)
        self._gk_carry_timer = max(0.0, self._gk_carry_timer - dt)
        self._frozen = {i: t - dt for i, t in self._frozen.items() if t - dt > 0.0}
        self._throw_wait_timer = max(0.0, self._throw_wait_timer - dt)
        self._reception_timer = max(0.0, self._reception_timer - dt)
        self._support_run_timer = max(0.0, self._support_run_timer - dt)
        self._cross_flight_timer = max(0.0, self._cross_flight_timer - dt)
        self._acquire_possession()
        self._resolve_tackle()  # un defensor pegado puede intentar quitar
        self._move_players(dt)  # la accion del que lleva puede soltar la pelota
        self._update_ball(dt)
        self._move_referee(dt)
        self.state.clock += dt
        self._tick += 1

    def run(self, duration: float, dt: float = DEFAULT_DT) -> None:
        """Avanza `duration` segundos en pasos de `dt`."""
        for _ in range(int(round(duration / dt))):
            self.step(dt)

    def _log(self, kind: str, player=None, team: Side | None = None,
             target=None, detail: str | None = None) -> None:
        """Registra un evento estructurado del partido (para el relato)."""
        self.state.log.append(
            MatchEvent(
                tick=self._tick,
                clock=self.state.clock,
                kind=kind,
                team=team or (player.team if player is not None else None),
                player=player.name if player is not None else None,
                target=target.name if target is not None else None,
                detail=detail,
            )
        )

    # --- Internos ---

    def _kickoff(self) -> None:
        """Saca del medio: un jugador en el centro le PASA a un companero (no sale
        la pelota de la nada). Saca el equipo que corresponde (`_kickoff_side`)."""
        state = self.state
        team = state.team(self._kickoff_side)
        outfield = [mp for mp in team if not ai.is_goalkeeper(mp)]
        pool = outfield or team
        center = state.pitch.center
        kicker = min(pool, key=lambda mp: mp.position.distance_to(center))
        kicker.position = center  # ya venia caminando al centro en la pausa
        state.ball.position = center
        state.ball.owner = None
        # Le toca a un companero cercano (no el arquero): el saque es un pase.
        mates = [mp for mp in pool if mp is not kicker]
        target = min(mates, key=lambda mp: mp.position.distance_to(kicker.position))
        self._restart_side = None
        self._restart_kind = None
        self._restart_taker = kicker  # queda quieto un instante tras tocarla
        self._log("pase", player=kicker, target=target, detail="corto")
        self._kick(kicker, target.position, _PASS_SPEED)
        self._set_reception(kicker, target)
        state.phase = MatchPhase.PLAYING

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
            taker = min(on_ball, key=lambda mp: mp.position.distance_to(ball.position))
            speed = ball.velocity.length()
            # Arquero ante un remate: puede que se le escape y siga de largo
            # (posible gol), o que la ataje limpio / de rebote (segun atributos).
            if ai.is_goalkeeper(taker) and speed > _SHOT_SAVE_SPEED:
                if self._rng.random() < self._gk_beaten_chance(taker):
                    # Se le escapa: no la domina, la pelota sigue (puede entrar).
                    self._kick_cooldown = max(self._kick_cooldown, 0.3)
                    self._log("escapa", player=taker)
                    return
                self._goalkeeper_save(taker)
                return
            # Mano (rareza): controlar una pelota rapida con la mano, muy de vez en cuando.
            if speed > _HANDBALL_SPEED and self._rng.random() < _HANDBALL_CHANCE:
                self._award_handball(taker)
                return
            was_restart = self._restart_side is not None
            prev_touch = self.state.last_touch
            ball.owner = taker
            ball.velocity = Vec2(0.0, 0.0)
            self.state.last_touch = taker.team
            self._restart_side = None  # pelota en juego de nuevo
            # En juego (no en un saque), si la toma el rival del ultimo toque
            # es una recuperacion/intercepcion.
            if not was_restart and prev_touch is not None and prev_touch is not taker.team:
                self._log("intercepta", player=taker)
            # Si tomo un saque pendiente, es el ejecutante (hasta que la juega).
            if was_restart:
                self._restart_taker = taker
                if self._restart_kind == "lateral" and not ai.is_goalkeeper(taker):
                    self._throw_wait_timer = _THROW_WAIT_MAX  # espera ayuda
            # El arquero que toma la pelota la "camina" un rato antes de distribuir.
            if ai.is_goalkeeper(taker):
                self._gk_carry_timer = _GK_CARRY_TIME

    def _gk_beaten_chance(self, gk) -> float:
        """Prob. de que al arquero se le escape un remate (peor reflejos/manos -> mas)."""
        quality = (gk.player.reflexes + gk.player.handling) / 2.0
        return _clamp(0.28 - quality / 220.0, 0.02, 0.28)

    def _goalkeeper_save(self, gk) -> None:
        """El arquero ataja un remate: lo manda al corner, lo retiene, o da rebote."""
        ball = self.state.ball
        self.state.last_touch = gk.team
        own = ai.own_goal(self.state, gk.team)
        # Manotazo al palo: la tira AL CORNER (mas probable con buenos reflejos).
        p_corner = _clamp(0.12 + gk.player.reflexes / 500.0, 0.1, 0.30)
        if self._rng.random() < p_corner:
            self.state.last_event = "Atajada"
            self._log("atajada", player=gk)
            self._concede_corner(gk.team, ball.position.y)
            return
        p_hold = _clamp(0.40 + gk.player.handling / 150.0, 0.2, 0.92)
        if self._rng.random() < p_hold:
            # Atajada limpia: la retiene.
            ball.owner = gk
            ball.velocity = Vec2(0.0, 0.0)
            self._restart_side = None
            self._restart_timer = _SETTLE_SAVE
            self._gk_carry_timer = _GK_CARRY_TIME
            self.state.last_event = "Atajada"
            self._log("atajada", player=gk)
            return
        # Rebote: la despeja sin control, hacia afuera del arco y con angulo al azar.
        outward = ball.position - own
        if outward.length() < 1e-6:
            outward = Vec2(1.0, 0.0) if gk.team is Side.HOME else Vec2(-1.0, 0.0)
        outward = outward.normalized()
        angle = self._rng.uniform(-0.6, 0.6)
        cos, sin = math.cos(angle), math.sin(angle)
        direction = Vec2(
            outward.x * cos - outward.y * sin, outward.x * sin + outward.y * cos
        )
        ball.velocity = direction * _PARRY_SPEED
        ball.owner = None
        self._kick_cooldown = _KICK_COOLDOWN  # que no la re-agarre al instante
        self.state.last_event = "Rebote"
        self._log("rebote", player=gk)

    def _reach(self, mp) -> float:
        """Radio (m) al que un jugador domina la pelota; mayor para el arquero en su area."""
        if ai.is_goalkeeper(mp):
            own_area = self.state.pitch.penalty_area(mp.team is Side.HOME)
            if own_area.contains(mp.position):
                return _GK_REACH
        return _CONTROL_RADIUS

    def _resolve_tackle(self) -> None:
        """Si un defensor esta pegado al que lleva la pelota, intenta el quite."""
        if self._tackle_cooldown > 0.0:
            return
        carrier = self.state.ball.owner
        if carrier is None:
            return
        defenders = [
            mp
            for mp in self.state.team(_other(carrier.team))
            if not ai.is_goalkeeper(mp)
        ]
        if not defenders:
            return
        tackler = min(defenders, key=lambda mp: mp.position.distance_to(carrier.position))
        if tackler.position.distance_to(carrier.position) > _TACKLE_RADIUS:
            return
        self._tackle_cooldown = _TACKLE_COOLDOWN
        self._attempt_tackle(tackler, carrier)

    def _attempt_tackle(self, tackler, carrier) -> None:
        """Resuelve el quite: `tackling` vs `dribbling` (+`strength`). Puede ser falta."""
        t = tackler.player
        c = carrier.player
        p_win = _clamp(
            0.45 + (t.tackling - c.dribbling) / 220.0 + (t.strength - c.strength) / 600.0,
            0.08,
            0.85,
        )
        if self._rng.random() < p_win:
            # Quite limpio: el defensor se queda con la pelota; el otro queda
            # frenado un instante (perdio la pelota).
            ball = self.state.ball
            ball.owner = tackler
            ball.velocity = Vec2(0.0, 0.0)
            self.state.last_touch = tackler.team
            self.state.last_event = "Quite"
            self._log("quite", player=tackler)
            self._freeze(carrier, _recovery_freeze(c.agility, c.composure))
            return
        # Fallo: chance de falta (mayor si lo superaron o el tackler es flojo).
        p_foul = _clamp(0.20 + (c.dribbling - t.tackling) / 350.0, 0.05, 0.5)
        if self._rng.random() < p_foul:
            self._log("falta", player=tackler)
            self._award_free_kick(carrier)
        else:
            # Lo gambetearon / erro el quite: el defensor queda frenado un instante.
            self._freeze(tackler, _recovery_freeze(t.agility, t.anticipation))

    def _award_set_piece(self, spot: Vec2, attacking_side: Side, event: str) -> None:
        """Planta la pelota para `attacking_side`; si es dentro del area, es penal."""
        pitch = self.state.pitch
        defending = _other(attacking_side)
        spot = pitch.clamp(spot)
        if pitch.penalty_area(defending is Side.HOME).contains(spot):
            spot = pitch.penalty_spot(defending is Side.HOME)
            event = "Penal"
        ball = self.state.ball
        ball.owner = None
        ball.position = spot
        ball.velocity = Vec2(0.0, 0.0)
        self._restart_side = attacking_side
        self._tackle_cooldown = _FOUL_RECOVER
        self._restart_timer = _SETTLE_FREEKICK
        self._restart_kind = "penal" if event == "Penal" else "tiro_libre"
        self.state.last_event = event

    def _award_free_kick(self, victim) -> None:
        """Falta: la pelota se planta para el equipo que recibio la infraccion."""
        self._award_set_piece(victim.position, victim.team, "Tiro libre")

    def _award_handball(self, offender) -> None:
        """Mano: tiro libre (o penal) para el rival del que la toco con la mano."""
        self.state.last_touch = offender.team
        self._log("mano", player=offender)
        self._award_set_piece(
            self.state.ball.position, _other(offender.team), "Mano"
        )

    def _award_offside(self, owner, receiver) -> None:
        """Offside: tiro libre indirecto para la defensa desde donde estaba el adelantado."""
        defending = _other(owner.team)
        ball = self.state.ball
        ball.owner = None
        ball.position = self.state.pitch.clamp(receiver.position)
        ball.velocity = Vec2(0.0, 0.0)
        self._restart_side = defending
        self._restart_timer = _SETTLE_RESTART
        self._restart_kind = "offside"
        self.state.last_touch = owner.team
        self.state.last_event = "Offside"
        self._log("offside", player=receiver)

    def _move_referee(self, dt: float) -> None:
        """El arbitro trota siguiendo la jugada, sin tocar la pelota."""
        ref = self.state.referee
        ref.velocity = ai.referee_velocity(ref, self.state)
        ref.position = self.state.pitch.clamp(ref.position + ref.velocity * dt)

    def _move_players(self, dt: float) -> None:
        # Si se acaba de cobrar una pelota muerta en este mismo tick, no se juega:
        # todos se reposicionan (la pausa la maneja el branch de settle en step).
        if self._restart_timer > 0.0:
            self._reposition_dead_ball(dt)
            return
        state = self.state
        owner = state.ball.owner
        if owner is None:
            if self._restart_side is not None:
                # Saque pendiente y todavia nadie la tomo (el ejecutante no llego a
                # la pelota en la pausa): sigue yendo a buscarla, no se va andando.
                self._reposition_dead_ball(dt)
            elif self._cross_flight_timer > 0.0 and self._crossing_side is not None:
                self._move_cross_flight(dt)
            else:
                self._move_loose_ball(dt)
        else:
            self._move_with_owner(dt, owner)

    def _set_reception(self, passer, target) -> None:
        """Tras un saque/pase de saque: el receptor va a buscar la pelota."""
        self._reception_id = id(target)
        self._reception_passer_id = id(passer)
        self._reception_timer = _RECEPTION_TIME

    def _move_loose_ball(self, dt: float) -> None:
        """Pelota suelta: cada equipo manda a su mas cercano; el resto sostiene."""
        state = self.state
        pitch = state.pitch
        chasers = {
            id(ai.team_ball_chaser(state, Side.HOME)),
            id(ai.team_ball_chaser(state, Side.AWAY)),
        }
        # Tras un saque: el receptor va a buscarla y el que la jugo no la persigue.
        if self._reception_timer > 0.0:
            if self._reception_id is not None:
                chasers.add(self._reception_id)
            chasers.discard(self._reception_passer_id)
        for mp in state.all_players():
            if self._is_support_runner(mp):
                mp.velocity = ai.support_run_velocity(mp, state)  # el que paso pica de apoyo
            elif ai.is_goalkeeper(mp):
                mp.velocity = ai.goalkeeper_velocity(mp, state)
            else:
                mp.velocity = ai.decide_velocity(mp, state, id(mp) in chasers)
            if self._is_frozen(mp):
                mp.velocity = Vec2(0.0, 0.0)
            mp.position = pitch.clamp(mp.position + mp.velocity * dt)

    def _is_support_runner(self, mp) -> bool:
        """Si este jugador acaba de pasar y esta picando de apoyo."""
        return self._support_run_timer > 0.0 and id(mp) == self._support_runner_id

    def _begin_cross_flight(self, side) -> None:
        """Arranca la ventana del centro: el equipo `side` ataca el area."""
        self._crossing_side = side
        self._cross_flight_timer = _CROSS_FLIGHT_TIME

    def _move_cross_flight(self, dt: float) -> None:
        """Centro en el aire: el que centro mete gente al area, la defensa marca.

        El mas cercano de cada equipo va a la pelota (a cabecear / despejar); del
        equipo que ataca, los centrales del frente llegan al area; la defensa
        marca (sus rivales mas peligrosos / el area). El resto sostiene.
        """
        state = self.state
        pitch = state.pitch
        atk = self._crossing_side
        chasers = {
            id(ai.team_ball_chaser(state, Side.HOME)),
            id(ai.team_ball_chaser(state, Side.AWAY)),
        }
        for mp in state.all_players():
            if id(mp) in chasers:
                vel = ai.decide_velocity(mp, state, is_chaser=True)
            elif ai.is_goalkeeper(mp):
                vel = ai.goalkeeper_velocity(mp, state)
            elif mp.team is atk and mp.role in (Role.STRIKER, Role.MIDFIELDER, Role.WINGER):
                vel = ai.box_crash_velocity(mp, state)  # llega al area al centro
            elif mp.team is not atk:
                vel = ai.marking_velocity(mp, state)     # la defensa marca
            else:
                vel = ai.decide_velocity(mp, state, is_chaser=False)
            if self._is_frozen(mp):
                vel = Vec2(0.0, 0.0)
            mp.velocity = vel
            mp.position = pitch.clamp(mp.position + vel * dt)

    def _is_frozen(self, mp) -> bool:
        """Si este jugador esta congelado un instante (saque, gambeteado, despojado)."""
        return self._frozen.get(id(mp), 0.0) > 0.0

    def _freeze(self, player, duration: float) -> None:
        """Deja a un jugador quieto `duration` segundos (no pisa uno mas largo)."""
        self._frozen[id(player)] = max(self._frozen.get(id(player), 0.0), duration)

    def _move_with_owner(self, dt: float, owner) -> None:
        """Hay dueno: un equipo ataca; el otro presiona la pelota y marca."""
        state = self.state
        pitch = state.pitch
        defending = _other(owner.team)
        presser = ai.team_ball_chaser(state, defending)
        # Si esta ejecutandose un lateral, los companeros cercanos siguen yendo a
        # ofrecerse adentro del campo (no se van al ataque hasta que se juega).
        offers = {}
        if owner is self._restart_taker and self._restart_kind == "lateral":
            offers = self._throw_in_offers(owner.team, owner, owner.position)
        # Mientras el ejecutante del corner espera, su opcion corta se queda cerca.
        if owner is self._restart_taker and self._restart_kind == "corner":
            rec, pt = self._corner_short_offer(owner.team, owner, owner.position)
            if rec is not None:
                offers = {id(rec): pt}
        for mp in state.all_players():
            if mp is owner:
                mp.velocity = self._owner_action(mp)
            elif ai.is_goalkeeper(mp):
                mp.velocity = ai.goalkeeper_velocity(mp, state)
            elif id(mp) in offers:
                mp.velocity = ai.arrive(mp.position, offers[id(mp)], ai.max_speed(mp.player))
            elif mp.team is defending:
                # Uno presiona la pelota; el resto marca su zona/rival.
                if mp is presser:
                    mp.velocity = ai.decide_velocity(mp, state, is_chaser=True)
                else:
                    mp.velocity = ai.marking_velocity(mp, state)
            elif self._is_support_runner(mp):
                # El que acaba de pasar pica de apoyo (pared / te paso y voy).
                mp.velocity = ai.support_run_velocity(mp, state)
            else:
                # Companero del que tiene la pelota: se desmarca (sube y busca espacio).
                mp.velocity = ai.attacking_run_velocity(mp, state)
            if self._is_frozen(mp):
                mp.velocity = Vec2(0.0, 0.0)
            mp.position = pitch.clamp(mp.position + mp.velocity * dt)

    def _settle(self, dt: float) -> None:
        """Pelota muerta: la pelota queda quieta y todos se reposicionan."""
        self._reposition_dead_ball(dt)
        ball = self.state.ball
        if ball.owner is not None:
            # El arquero (o quien la tenga) la sostiene mientras se acomodan.
            ball.position = ball.owner.position
        self._move_referee(dt)

    def _reposition_dead_ball(self, dt: float) -> None:
        """Mueve a todos a sus lugares del balon parado: ejecutante, barrera, area."""
        state = self.state
        pitch = state.pitch
        ball = state.ball
        owner = ball.owner
        taking = self._restart_side
        if taking is None and owner is not None:
            taking = owner.team
        spot = ball.position

        # Ejecutante: si alguien la tiene, es el; el saque de arco lo ejecuta el
        # arquero; el resto, el de campo mas cercano (camina hasta la pelota:
        # linea, corner, punto, etc.).
        taker = owner
        if taker is None and taking is not None:
            if self._restart_kind == "saque_arco":
                taker = ai.team_goalkeeper(state, taking)
            elif self._restart_kind in ("tiro_libre", "penal", "offside"):
                taker = self._free_kick_taker(taking, spot)
            if taker is None:
                outfield = [m for m in state.team(taking) if not ai.is_goalkeeper(m)]
                pool = outfield or state.team(taking)
                taker = min(pool, key=lambda m: m.position.distance_to(spot))

        # Barrera: solo en tiros libres a media distancia del arco que se defiende.
        wall_ids: set[int] = set()
        if taking is not None:
            goal_def = ai.own_goal(state, _other(taking))
            if _WALL_MIN < spot.distance_to(goal_def) < _WALL_MAX:
                wp = self._wall_point(spot, goal_def)
                defs = [m for m in state.team(_other(taking)) if not ai.is_goalkeeper(m)]
                for m in sorted(defs, key=lambda m: m.position.distance_to(wp))[:2]:
                    wall_ids.add(id(m))

        # Lateral: un par de companeros cercanos van a ofrecerse ADENTRO del campo
        # y los rivales que tienen cerca intentan marcarlos (goal-side).
        offers = self._throw_in_offers(taking, taker, spot) if self._restart_kind == "lateral" else {}
        throw_marks = self._throw_in_marks(taking, offers) if self._restart_kind == "lateral" else {}

        # Corner: un companero se queda cerca de la esquina como opcion de pase corto,
        # y SUBE casi todo el equipo al area (incluido un central a cabecear); un
        # central de resguardo se queda atras. La defensa marca el area.
        corner_short: dict = {}
        corner_crash: set = set()
        keep_back = None
        if self._restart_kind == "corner" and taking is not None:
            rec, pt = self._corner_short_offer(taking, taker, spot)
            if rec is not None:
                corner_short[id(rec)] = pt
            mates = [
                m for m in state.team(taking)
                if not ai.is_goalkeeper(m) and m is not taker and id(m) not in corner_short
            ]
            cbs = [m for m in mates if m.role is Role.CENTER_BACK]
            if cbs:  # el central peor de cabeza se queda de resguardo, el resto sube
                keep_back = min(cbs, key=lambda m: m.player.heading)
            corner_crash = {id(m) for m in mates if m is not keep_back}

        for mp in state.all_players():
            if mp is taker and owner is None:
                vel = ai.arrive(mp.position, spot, ai.max_speed(mp.player))
            elif ai.is_goalkeeper(mp):
                vel = ai.goalkeeper_velocity(mp, state)
            elif id(mp) in offers:
                vel = ai.arrive(mp.position, offers[id(mp)], ai.max_speed(mp.player))
            elif id(mp) in corner_short:
                vel = ai.arrive(mp.position, corner_short[id(mp)], ai.max_speed(mp.player))
            elif id(mp) in corner_crash:
                vel = ai.box_crash_velocity(mp, state)  # sube al area a cabecear
            elif self._restart_kind == "corner" and taking is not None and mp.team is _other(taking):
                vel = ai.marking_velocity(mp, state)    # la defensa marca el area
            elif id(mp) in throw_marks:
                vel = ai.arrive(mp.position, throw_marks[id(mp)], ai.max_speed(mp.player))
            elif id(mp) in wall_ids:
                wp = self._wall_point(spot, ai.own_goal(state, mp.team))
                vel = ai.arrive(mp.position, wp, ai.max_speed(mp.player))
            elif taking is not None and mp.team is taking and self._in_attacking_third(spot, taking):
                # El equipo que saca cerca del area rival: se tiran al ataque.
                vel = ai.attacking_run_velocity(mp, state)
            else:
                vel = ai.decide_velocity(mp, state, is_chaser=False)
            mp.velocity = vel
            mp.position = pitch.clamp(mp.position + vel * dt)

    def _free_kick_taker(self, taking, spot: Vec2):
        """Quien patea el tiro libre: el mejor pasador/pateador cerca de la pelota
        (corre hasta ella). Mas adelante sera una opcion seteable antes del partido."""
        pool = [m for m in self.state.team(taking) if not ai.is_goalkeeper(m)]
        if not pool:
            return None
        near = [m for m in pool if m.position.distance_to(spot) < 18.0]
        if near:
            return max(near, key=lambda m: m.player.passing + m.player.shooting)
        return min(pool, key=lambda m: m.position.distance_to(spot))

    def _corner_short_offer(self, taking, taker, spot: Vec2):
        """Companero que se ofrece para un corner CORTO (engano) y donde se para.

        Devuelve (jugador, punto) o (None, None). Es el companero mas cercano a la
        esquina (sin contar al ejecutante): se para a ~9m adentro, cerca del fondo.
        """
        if taking is None or taker is None:
            return None, None
        mates = [m for m in self.state.team(taking) if m is not taker and not ai.is_goalkeeper(m)]
        if not mates:
            return None, None
        receiver = min(mates, key=lambda m: m.position.distance_to(spot))
        pitch = self.state.pitch
        inward = 1.0 if spot.y < pitch.width / 2 else -1.0
        toward = 1.0 if taking is Side.HOME else -1.0
        point = pitch.clamp(Vec2(spot.x - toward * 2.0, spot.y + inward * 9.0))
        return receiver, point

    def _throw_in_offers(self, taking, taker, spot: Vec2) -> dict:
        """Puntos donde se ofrecen los companeros cercanos en un saque de banda."""
        if taking is None or taker is None:
            return {}
        pitch = self.state.pitch
        inward = 1.0 if spot.y < pitch.width / 2 else -1.0  # hacia adentro del campo
        points = [
            pitch.clamp(Vec2(spot.x - 6.0, spot.y + inward * 8.0)),
            pitch.clamp(Vec2(spot.x + 6.0, spot.y + inward * 7.0)),
            pitch.clamp(Vec2(spot.x, spot.y + inward * 14.0)),
        ]
        candidates = [
            m for m in self.state.team(taking)
            if m is not taker and not ai.is_goalkeeper(m)
        ]
        candidates.sort(key=lambda m: m.position.distance_to(spot))
        return {id(m): p for m, p in zip(candidates, points)}

    def _throw_in_marks(self, taking, offers: dict) -> dict:
        """Rivales cercanos marcan (goal-side) a los companeros que se ofrecen."""
        if taking is None or not offers:
            return {}
        state = self.state
        rivals = [m for m in state.team(_other(taking)) if not ai.is_goalkeeper(m)]
        offered = [m for m in state.team(taking) if id(m) in offers]
        marks: dict = {}
        used: set[int] = set()
        for tm in offered:
            cand = [
                r for r in rivals
                if id(r) not in used and r.position.distance_to(tm.position) < 22.0
            ]
            if not cand:
                continue
            r = min(cand, key=lambda r: r.position.distance_to(tm.position))
            used.add(id(r))
            marks[id(r)] = ai.marking_point(r, tm, state)
        return marks

    def _wall_point(self, spot: Vec2, goal: Vec2) -> Vec2:
        """Punto de barrera: entre la pelota y el arco, a _WALL_DIST del balon."""
        return spot + (goal - spot).normalized() * _WALL_DIST

    def _in_attacking_third(self, spot: Vec2, side: Side) -> bool:
        """Si el punto esta en el ultimo tercio de ataque del equipo `side`."""
        length = self.state.pitch.length
        if side is Side.HOME:
            return spot.x > length * 2.0 / 3.0
        return spot.x < length / 3.0

    def _owner_action(self, owner) -> Vec2:
        """Decide que hace el que tiene la pelota; devuelve su velocidad."""
        state = self.state
        goal = ai.attacking_goal(state, owner.team)

        # Ejecutante de un lateral o corner: saque dedicado (hacia adentro / al area).
        if owner is self._restart_taker:
            if self._restart_kind == "lateral":
                # Espera a tener un companero al alcance (o si lo presionan / se
                # acaba el tiempo, saca igual hacia adentro).
                option = self._throw_option(owner)
                rival = ai.nearest_opponent(owner, state)
                pressured = rival.position.distance_to(owner.position) < _THROW_PRESSURE
                if option is None and not pressured and self._throw_wait_timer > 0.0:
                    return Vec2(0.0, 0.0)  # sostiene la pelota, espera ayuda
                self._take_throw_in(owner)
                return Vec2(0.0, 0.0)
            # El corner se ejecuta desde la pelota muerta (ver _execute_corner), no
            # en vivo: si por algun motivo se llega aca, se tira el centro.
            if self._restart_kind == "corner":
                self._take_corner(owner)
                return Vec2(0.0, 0.0)
            if self._restart_kind in ("tiro_libre", "penal", "offside"):
                # Tiro libre: se patea de verdad (remate o pase), no se sale gambeteando.
                self._take_free_kick(owner)
                return Vec2(0.0, 0.0)

        # Arquero con la pelota: camina el area buscando opcion y despues
        # distribuye (saque corto seguro o pelotazo largo). Si lo presionan, ya.
        if ai.is_goalkeeper(owner):
            rival = ai.nearest_opponent(owner, state)
            pressured = rival.position.distance_to(owner.position) < _GK_CARRY_PRESSURE
            if self._gk_carry_timer > 0.0 and not pressured:
                return ai.goalkeeper_carry_velocity(owner, state)
            self._goalkeeper_distribute(owner)
            return Vec2(0.0, 0.0)

        # Defensor que gana la pelota en su propia area bajo presion: la DESPEJA
        # (la saca lejos), de cabeza si venia un centro; un mal despeje se va al corner.
        if self._should_clear(owner):
            self._clear_ball(owner)
            return Vec2(0.0, 0.0)

        # Extremo o lateral por la banda: si esta abierto y BIEN PROFUNDO (cerca de
        # la linea de fondo), tira el CENTRO al area; si no, encara hacia el corner
        # (profundiza pegado a la banda) para tirar el centro desde el fondo.
        if owner.role in (Role.WINGER, Role.FULLBACK) and self._is_wide(owner):
            if self._in_crossing_zone(owner):
                self._cross(owner)
                return Vec2(0.0, 0.0)
            toward = 1.0 if owner.team is Side.HOME else -1.0
            w = state.pitch.width
            touch_y = 5.0 if owner.position.y < w / 2 else w - 5.0  # se pega a la banda
            corner = state.pitch.clamp(Vec2(owner.position.x + toward * 9.0, touch_y))
            return ai.arrive(owner.position, corner, ai.max_speed(owner.player) * _DRIBBLE_FACTOR)

        # Dentro de su alcance de remate (segun shooting) -> remata.
        if owner.position.distance_to(goal) <= ai.shoot_range(owner.player):
            self._shoot(owner, goal)
            return Vec2(0.0, 0.0)

        # Pase de gol: si un companero esta mejor ubicado para definir, asistir...
        # ...salvo que el jugador decida jugarla individual (mas si es gambeteador).
        assist = ai.better_finisher(owner, state, _MAX_PASS_DIST)
        if assist is not None and not self._goes_individual(owner):
            if ai.is_offside(assist, owner, state):
                self._award_offside(owner, assist)
            else:
                self._pass(owner, assist, ai.is_long_pass(owner, assist))
            return Vec2(0.0, 0.0)

        # Presionado -> pase (corto o largo) al mejor companero, o remate si no hay.
        rival = ai.nearest_opponent(owner, state)
        if rival.position.distance_to(owner.position) < _PRESSURE_RADIUS:
            pick = ai.pick_pass(owner, state, _MAX_PASS_DIST)
            if pick is not None:
                mate, is_long = pick
                if ai.is_offside(mate, owner, state):
                    self._award_offside(owner, mate)
                else:
                    self._pass(owner, mate, is_long)
            else:
                self._kick(owner, goal, _SHOOT_SPEED)
            return Vec2(0.0, 0.0)

        # Libre -> abre el juego a un extremo libre para atacar por la banda.
        winger = ai.open_winger(owner, state, _MAX_PASS_DIST)
        if (
            winger is not None
            and owner.role is not Role.WINGER
            and self._rng.random() < _WING_SEEK_CHANCE
        ):
            self._pass(owner, winger, ai.is_long_pass(owner, winger))
            return Vec2(0.0, 0.0)

        # Libre -> de vez en cuando cambia el juego a un companero muy solo en otra
        # zona (lateral / diagonal), para que el balon se mueva por la cancha.
        outlet = ai.open_outlet(owner, state, _MAX_PASS_DIST)
        if (
            outlet is not None
            and not ai.is_offside(outlet, owner, state)
            and self._rng.random() < _clamp(0.008 + owner.player.vision / 3000.0, 0.008, 0.04)
        ):
            self._pass(owner, outlet, ai.is_long_pass(owner, outlet))
            return Vec2(0.0, 0.0)

        # Si no, gambetea hacia el arco (se va acercando para definir mejor).
        return ai.arrive(
            owner.position, goal, ai.max_speed(owner.player) * _DRIBBLE_FACTOR
        )

    def _goes_individual(self, owner) -> bool:
        """Si el jugador decide jugarla solo en vez de dar el pase de gol.

        Pasa a veces en el futbol: mas probable en gambeteadores, menos en los de
        buena vision/juego colectivo.
        """
        p = owner.player
        chance = _clamp(0.15 + (p.dribbling - p.vision) / 300.0, 0.05, 0.45)
        return self._rng.random() < chance

    def _throw_option(self, taker):
        """Companero ya al alcance del saque de banda (adentro del campo y libre)."""
        pitch = self.state.pitch
        rivals = self.state.team(_other(taker.team))
        best = None
        best_open = 4.0
        for m in self.state.team(taker.team):
            if m is taker or ai.is_goalkeeper(m):
                continue
            if m.position.distance_to(taker.position) > _THROW_OPTION_RANGE:
                continue
            if not (4.0 < m.position.y < pitch.width - 4.0):
                continue
            openness = min(
                (o.position.distance_to(m.position) for o in rivals), default=999.0
            )
            if openness > best_open:
                best, best_open = m, openness
        return best

    def _take_throw_in(self, taker) -> None:
        """Saque de banda: pase corto SIEMPRE hacia adentro del campo (no sale)."""
        state = self.state
        pitch = state.pitch
        spot = taker.position
        rivals = state.team(_other(taker.team))
        # Companeros adentro del campo, cerca, abiertos (los que se ofrecieron).
        mates = [
            m for m in state.team(taker.team)
            if m is not taker
            and m.position.distance_to(spot) <= 25.0
            and 4.0 < m.position.y < pitch.width - 4.0
        ]
        if mates:
            target = max(
                mates,
                key=lambda m: min(
                    (o.position.distance_to(m.position) for o in rivals), default=999.0
                ),
            )
            aim = target.position + self._pass_error(taker.player, is_long=False)
        else:
            target = None
            aim = Vec2(spot.x, pitch.width / 2)  # si no hay, hacia el centro
        # El saque nunca puede salir directo: se acota bien adentro de la cancha.
        aim = Vec2(
            min(max(aim.x, 3.0), pitch.length - 3.0),
            min(max(aim.y, 4.0), pitch.width - 4.0),
        )
        self._log("pase", player=taker, target=target, detail="corto")
        self._kick(taker, aim, _PASS_SPEED)
        if target is not None:
            self._set_reception(taker, target)

    def _is_wide(self, mp) -> bool:
        """Si el jugador esta pegado a una banda."""
        w = self.state.pitch.width
        return mp.position.y < _WIDE_MARGIN or mp.position.y > w - _WIDE_MARGIN

    def _in_crossing_zone(self, mp) -> bool:
        """Si el que la lleva esta abierto Y cerca de la linea de fondo (profundo)."""
        goal = ai.attacking_goal(self.state, mp.team)
        depth = abs(goal.x - mp.position.x)  # cercania a la linea de fondo (en x)
        deep = depth < self.state.pitch.length * _CROSS_ZONE
        return self._is_wide(mp) and deep

    def _cross(self, winger) -> None:
        """Centro del que llego al fondo: al area (punto penal) o ATRAS (cut-back).

        Desde bien pegado a la linea de fondo, a veces la tira atras al borde del
        area (cut-back) donde llega un volante, en vez del centro alto al area.
        """
        state = self.state
        pitch = state.pitch
        is_home = winger.team is Side.HOME
        goal = ai.attacking_goal(state, winger.team)
        depth = abs(goal.x - winger.position.x)
        toward = 1.0 if is_home else -1.0
        if depth < 6.0 and self._rng.random() < 0.45:
            # Cut-back: centro atras al borde del area, para el que llega de frente.
            target = Vec2(goal.x - toward * 11.0, pitch.width / 2)
            detail = " atras"
        else:
            target = pitch.penalty_spot(home=not is_home)
            detail = None
        aim = target + self._pass_error(winger.player, is_long=True)
        self._log("centro", player=winger, detail=detail)
        self._kick(winger, aim, _CROSS_SPEED)
        self._begin_cross_flight(winger.team)

    def _take_free_kick(self, taker) -> None:
        """Ejecuta un tiro libre: remata si esta cerca y de frente, si no la juega.

        Nunca se sale gambeteando: o va al arco, o es un pase (al mejor companero
        que progresa) o un pelotazo al area. El penal siempre es remate.
        """
        state = self.state
        goal = ai.attacking_goal(state, taker.team)
        dist = taker.position.distance_to(goal)
        if self._restart_kind == "penal" or dist <= _FREE_KICK_SHOOT_RANGE:
            self._shoot(taker, goal)
            return
        pick = ai.pick_pass(taker, state, _MAX_PASS_DIST * 1.6)
        if pick is not None:
            mate, is_long = pick
            if not ai.is_offside(mate, taker, state):
                self._pass(taker, mate, is_long)
                return
        # Sin opcion clara: pelotazo adelante / al area (clamp adentro del campo).
        target = ai.best_pass_target(taker, state, _MAX_PASS_DIST * 2.0)
        dest = target.position if target is not None else goal
        dest = self._inbounds_target(dest)
        self._log("pase", player=taker, target=target, detail="largo")
        self._kick(taker, dest, _LONG_PASS_SPEED)

    def _box_attackers(self, side: Side) -> int:
        """Cuantos jugadores de `side` estan dentro del area rival (esperando)."""
        state = self.state
        goal = ai.attacking_goal(state, side)
        margin = 14.0
        return sum(
            1 for m in state.team(side)
            if abs(m.position.x - goal.x) < 16.5
            and margin < m.position.y < state.pitch.width - margin
        )

    def _concede_corner(self, defending: Side, near_y: float) -> None:
        """Concede un corner al rival de `defending` (saque desde la esquina)."""
        state = self.state
        pitch = state.pitch
        own = ai.own_goal(state, defending)
        corner_y = 0.0 if near_y < pitch.width / 2 else pitch.width
        spot = Vec2(_nudge_inside(own.x, pitch.length), _nudge_inside(corner_y, pitch.width))
        ball = state.ball
        ball.position = spot
        ball.velocity = Vec2(0.0, 0.0)
        ball.owner = None
        self._restart_side = _other(defending)
        self._restart_timer = _SETTLE_RESTART
        self._restart_kind = "corner"
        self._corner_setup = 0.0
        state.last_event = "Corner"
        self._log("corner", team=_other(defending))

    def _should_clear(self, owner) -> bool:
        """Si un defensor gano la pelota en su propia area con un rival encima."""
        state = self.state
        area = state.pitch.penalty_area(owner.team is Side.HOME)
        if not area.contains(owner.position):
            return False
        rival = ai.nearest_opponent(owner, state)
        return rival.position.distance_to(owner.position) < _CLEAR_PRESSURE

    def _clear_ball(self, owner) -> None:
        """Despeje del defensor: la saca lejos del arco propio; un mal despeje (poca
        composure, mas si la cabecea) se va por su linea de fondo = corner rival."""
        state = self.state
        pitch = state.pitch
        own = ai.own_goal(state, owner.team)
        header = self._cross_flight_timer > 0.0
        detail = " de cabeza" if header else None
        panic = _clamp(0.10 - owner.player.composure / 1200.0, 0.02, 0.12)
        if header:
            panic += 0.05
        if self._rng.random() < panic:
            # Mal despeje: la manda por su propia linea de fondo -> corner rival.
            self._log("despeje", player=owner, detail=detail)
            self._concede_corner(owner.team, owner.position.y)
            return
        # Despeje normal: lejos del arco propio (arriba) y a un costado, con dispersion.
        toward = 1.0 if owner.team is Side.HOME else -1.0
        side = 1.0 if owner.position.y < pitch.width / 2 else -1.0
        aim = Vec2(owner.position.x + toward * 32.0, owner.position.y + side * 10.0)
        aim = self._inbounds_target(aim + self._pass_error(owner.player, is_long=True))
        self._log("despeje", player=owner, detail=detail)
        self._kick(owner, aim, _CLEAR_SPEED)

    def _inbounds_target(self, dest: Vec2) -> Vec2:
        """Acota un destino de pelotazo bien adentro del campo (no se va al lateral)."""
        pitch = self.state.pitch
        return Vec2(
            min(max(dest.x, 3.0), pitch.length - 3.0),
            min(max(dest.y, 8.0), pitch.width - 8.0),
        )

    def _execute_corner(self) -> None:
        """Ejecuta el corner desde la pelota muerta (ya con el area llena): centro
        al area, o de vez en cuando CORTO (engano) a un companero junto a la esquina."""
        state = self.state
        taking = self._restart_side
        spot = state.ball.position
        outfield = [m for m in state.team(taking) if not ai.is_goalkeeper(m)]
        pool = outfield or state.team(taking)
        taker = min(pool, key=lambda m: m.position.distance_to(spot))
        # Sale de la pelota muerta: a partir de aca la pelota esta viva.
        self._restart_timer = 0.0
        self._restart_kind = None
        self._restart_side = None
        self._restart_taker = None
        rec, _pt = self._corner_short_offer(taking, taker, spot)
        if rec is not None and self._rng.random() < 0.22:
            self._log("pase", player=taker, target=rec, detail="corto")
            self._kick(taker, rec.position, _PASS_SPEED)
            self._set_reception(taker, rec)
        else:
            self._take_corner(taker)

    def _take_corner(self, taker) -> None:
        """Corner: centro al area rival (donde los companeros se tiraron al ataque)."""
        state = self.state
        is_home = taker.team is Side.HOME
        # Punto penal del arco rival (centro del area que ataca).
        target = state.pitch.penalty_spot(home=not is_home)
        aim = target + self._pass_error(taker.player, is_long=True)
        self._log("centro", player=taker)
        self._kick(taker, aim, _LONG_PASS_SPEED)
        self._begin_cross_flight(taker.team)

    def _goalkeeper_distribute(self, gk) -> None:
        """El arquero reparte: saque corto a un companero libre, o pelotazo largo.

        Saca corto (mano/pie) si NO esta presionado, hay un companero libre y
        decide hacerlo (mas probable con buen `passing`/`composure`); si no,
        revienta largo hacia un companero adelantado o el area rival.
        """
        state = self.state
        rival = ai.nearest_opponent(gk, state)
        # Solo sale jugando corto si NO hay presion cerca; bajo presion la revienta
        # larga (si no, un delantero camped recupera y se arma un loop irreal).
        safe = rival.position.distance_to(gk.position) > _GK_SHORT_SAFE
        short = ai.goalkeeper_short_option(gk, state)
        p = gk.player
        plays_short = (
            safe
            and short is not None
            and self._rng.random() < _clamp(0.2 + (p.passing + p.composure) / 400.0, 0.1, 0.85)
        )
        if plays_short:
            aim = short.position + self._pass_error(p, is_long=False)
            self._log("saque_corto", player=gk, target=short)
            self._kick(gk, aim, _PASS_SPEED)
        else:
            target = ai.best_pass_target(gk, state, _MAX_PASS_DIST * 2.0)
            dest = target.position if target is not None else ai.attacking_goal(state, gk.team)
            dest = self._inbounds_target(dest)  # el saque/despeje no se va al lateral
            self._log("despeje", player=gk)
            self._kick(gk, dest, _CLEAR_SPEED)

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
        # Remate de primera tras un centro (cabezazo/volea): mucho mas dificil de
        # acomodar -> menos punteria y mas dispersion (no todo centro es gol).
        off_cross = self._cross_flight_timer > 0.0
        if off_cross:
            accuracy *= 0.5
        dist = owner.position.distance_to(goal)
        # Si viene de un centro/corner en el aire, es un cabezazo (se ve en el relato).
        self._log("cabezazo" if off_cross else "remate", player=owner)
        # El arquero achica el angulo y tapa la MAYORIA de los remates (segun sus
        # reflejos/posicion vs la jerarquia del tirador). Si "ataja", la pelota va
        # hacia el (la atrapa o da rebote en _acquire_possession). Si no, va al palo
        # lejano (y la dispersion puede irse afuera). Asi no todo remate es gol.
        if keeper is not None and self._rng.random() < self._shot_save_chance(owner, keeper, dist):
            target_y = keeper.position.y + self._rng.uniform(-1.0, 1.0) * 1.5
            self._kick(owner, Vec2(goal.x, target_y), _SHOOT_SPEED)
            return
        target_y = goal.y + aim_side * half * (0.4 + 0.6 * accuracy)
        spread = (1.0 - accuracy) * half * 1.5
        if off_cross:
            spread *= 2.0
        target_y += self._rng.uniform(-1.0, 1.0) * spread
        self._kick(owner, Vec2(goal.x, target_y), _SHOOT_SPEED)

    def _shot_save_chance(self, shooter, keeper, dist: float) -> float:
        """Prob. de que el arquero tape el remate: ancla de liga + atributos.

        Sube con reflejos/posicionamiento del arquero, baja con el shooting del
        tirador, y de lejos es mas atajable (mas tiempo de reaccion) que de cerca.
        """
        gk = (keeper.player.reflexes + keeper.player.positioning) / 2.0
        chance = (
            _SAVE_BASE
            + (gk - 55.0) / 250.0
            - (shooter.player.shooting - 55.0) / 250.0
            + _clamp((dist - 16.0) / 120.0, -0.08, 0.08)
        )
        return _clamp(chance, 0.2, 0.93)

    def _pass(self, owner, mate, is_long: bool) -> None:
        """Pasa la pelota a un companero, con error segun `passing` del que pasa.

        El pase largo va mas rapido y se desvia mas. Un pase desviado puede
        terminar en un rival (intercepcion) o salir del campo (lateral): la
        pelota queda en lugares que hay que ir a buscar.
        """
        speed = _LONG_PASS_SPEED if is_long else _PASS_SPEED
        aim = mate.position + self._pass_error(owner.player, is_long)
        self._log("pase", player=owner, target=mate,
                  detail="largo" if is_long else "corto")
        self._kick(owner, aim, speed)
        # Pase corto -> el que paso pica de apoyo (pared / te paso y voy).
        if not is_long:
            self._support_runner_id = id(owner)
            self._support_run_timer = _SUPPORT_RUN_TIME

    def _pass_error(self, player, is_long: bool) -> Vec2:
        """Desvio del pase: inversamente proporcional a `passing`, mayor si es largo."""
        inaccuracy = 1.0 - player.passing / 100.0
        max_off = (_LONG_PASS_ERROR if is_long else _SHORT_PASS_ERROR) * inaccuracy
        if max_off <= 0.0:
            return Vec2(0.0, 0.0)
        angle = self._rng.uniform(0.0, 2.0 * math.pi)
        radius = self._rng.uniform(0.0, max_off)
        return Vec2(math.cos(angle) * radius, math.sin(angle) * radius)

    def _kick(self, kicker, target: Vec2, speed: float) -> None:
        """Patea la pelota desde `kicker` hacia `target` y la suelta."""
        ball = self.state.ball
        ball.velocity = (target - kicker.position).normalized() * speed
        ball.owner = None
        self.state.last_touch = kicker.team
        self._last_kicker = kicker
        self._kick_cooldown = _KICK_COOLDOWN
        # El ejecutante de un saque queda quieto un instante tras jugarla (no se
        # mueve a la vez que pasa, que parece que se la lleva).
        if kicker is self._restart_taker:
            self._freeze(kicker, _TAKER_FREEZE)
            self._restart_taker = None

    def _update_ball(self, dt: float) -> None:
        state = self.state
        ball = state.ball

        # Pelota muerta recien cobrada: queda quieta (o pegada al que la sostiene).
        if self._restart_timer > 0.0:
            if ball.owner is not None:
                ball.position = ball.owner.position
            return

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
        self._restart_timer = _SETTLE_RESTART
        self._restart_kind = {
            "Lateral": "lateral", "Corner": "corner", "Saque de arco": "saque_arco"
        }[event]
        self._corner_setup = 0.0
        state.last_event = event
        self._log(
            {"Lateral": "lateral", "Corner": "corner", "Saque de arco": "saque_arco"}[event],
            team=restart_side,
        )

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
        self._log("gol", player=self._last_kicker, team=side)
        self._kickoff_side = _other(side)  # saca del medio el que recibio el gol
        self._reset_for_kickoff()

    def _reset_for_kickoff(self) -> None:
        """Prepara el saque del medio: la pelota al centro y todos CORREN a su
        formacion (no se teletransportan); el que saca camina hasta la pelota."""
        state = self.state
        for mp in state.all_players():
            mp.velocity = Vec2(0.0, 0.0)  # arrancan quietos y corren a su lugar
        ball = state.ball
        ball.owner = None
        ball.position = state.pitch.center
        ball.velocity = Vec2(0.0, 0.0)
        self._kick_cooldown = 0.0
        self._tackle_cooldown = 0.0
        self._restart_side = self._kickoff_side  # el que saca camina al centro
        self._restart_timer = _SETTLE_KICKOFF
        self._restart_kind = "kickoff"
        state.phase = MatchPhase.KICKOFF
