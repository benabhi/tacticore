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
_MAX_PASS_DIST = 35.0     # alcance maximo de un pase (m)
_PASS_SPEED = 14.0        # velocidad de un pase corto (m/s)
_LONG_PASS_SPEED = 19.0   # velocidad de un pase largo (m/s)
_SHORT_PASS_ERROR = 3.0   # desvio maximo de un pase corto con passing=0 (m)
_LONG_PASS_ERROR = 8.0    # desvio maximo de un pase largo con passing=0 (m)
_SHOOT_SPEED = 25.0       # velocidad de un remate (m/s)
_DRIBBLE_FACTOR = 0.85    # se gambetea un poco mas lento que corriendo libre
_DRIBBLE_OFFSET = 0.5     # la pelota va esta distancia por delante del que lleva
_GK_REACH = 1.7           # el arquero domina la pelota a este radio dentro del area (m)
_CLEAR_SPEED = 24.0       # velocidad del despeje del arquero (m/s)
_GK_SHORT_SAFE = 24.0     # solo saca corto si el rival mas cercano esta a mas que esto (m)
_GK_CARRY_TIME = 2.5      # el arquero camina el area buscando opcion antes de distribuir (s)
_GK_CARRY_PRESSURE = 8.0  # si un rival se acerca mas que esto, distribuye ya (no camina)
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
        self._restart_is_goal_kick = False  # el saque pendiente es de arco (lo saca el GK)
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
            self.state.clock += dt
            self._tick += 1
            return
        if self.state.phase is MatchPhase.KICKOFF:
            self._kickoff()
        self._kick_cooldown = max(0.0, self._kick_cooldown - dt)
        self._tackle_cooldown = max(0.0, self._tackle_cooldown - dt)
        self._gk_carry_timer = max(0.0, self._gk_carry_timer - dt)
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
            # El arquero que toma la pelota la "camina" un rato antes de distribuir.
            if ai.is_goalkeeper(taker):
                self._gk_carry_timer = _GK_CARRY_TIME

    def _gk_beaten_chance(self, gk) -> float:
        """Prob. de que al arquero se le escape un remate (peor reflejos/manos -> mas)."""
        quality = (gk.player.reflexes + gk.player.handling) / 2.0
        return _clamp(0.28 - quality / 220.0, 0.02, 0.28)

    def _goalkeeper_save(self, gk) -> None:
        """El arquero ataja un remate: lo retiene (handling) o da rebote (pelota viva)."""
        ball = self.state.ball
        self.state.last_touch = gk.team
        p_hold = _clamp(0.35 + gk.player.handling / 150.0, 0.2, 0.95)
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
        own = ai.own_goal(self.state, gk.team)
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
            # Quite limpio: el defensor se queda con la pelota.
            ball = self.state.ball
            ball.owner = tackler
            ball.velocity = Vec2(0.0, 0.0)
            self.state.last_touch = tackler.team
            self.state.last_event = "Quite"
            self._log("quite", player=tackler)
            return
        # Fallo: chance de falta (mayor si lo superaron o el tackler es flojo).
        p_foul = _clamp(0.20 + (c.dribbling - t.tackling) / 350.0, 0.05, 0.5)
        if self._rng.random() < p_foul:
            self._log("falta", player=tackler)
            self._award_free_kick(carrier)

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
        self._restart_timer = _SETTLE_RESTART
        self._restart_is_goal_kick = False
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
        self._restart_is_goal_kick = False
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
                # Companero del que tiene la pelota: se desmarca (sube y busca espacio).
                mp.velocity = ai.attacking_run_velocity(mp, state)
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
            if self._restart_is_goal_kick:
                taker = ai.team_goalkeeper(state, taking)
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

        for mp in state.all_players():
            if mp is taker and owner is None:
                vel = ai.arrive(mp.position, spot, ai.max_speed(mp.player))
            elif ai.is_goalkeeper(mp):
                vel = ai.goalkeeper_velocity(mp, state)
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

        # Arquero con la pelota: camina el area buscando opcion y despues
        # distribuye (saque corto seguro o pelotazo largo). Si lo presionan, ya.
        if ai.is_goalkeeper(owner):
            rival = ai.nearest_opponent(owner, state)
            pressured = rival.position.distance_to(owner.position) < _GK_CARRY_PRESSURE
            if self._gk_carry_timer > 0.0 and not pressured:
                return ai.goalkeeper_carry_velocity(owner, state)
            self._goalkeeper_distribute(owner)
            return Vec2(0.0, 0.0)

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

        # Libre -> gambetea hacia el arco (se va acercando para definir mejor).
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
        target_y = goal.y + aim_side * half * (0.4 + 0.6 * accuracy)
        target_y += self._rng.uniform(-1.0, 1.0) * (1.0 - accuracy) * half * 1.5
        self._log("remate", player=owner)
        self._kick(owner, Vec2(goal.x, target_y), _SHOOT_SPEED)

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
        self._restart_is_goal_kick = event == "Saque de arco"
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
        self._tackle_cooldown = 0.0
        self._restart_side = None
        self._restart_timer = _SETTLE_KICKOFF
        self._restart_is_goal_kick = False
        state.phase = MatchPhase.KICKOFF
