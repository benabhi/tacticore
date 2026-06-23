"""IA de los jugadores en el partido (steering minimalista).

B3.1: cada equipo manda a perseguir la pelota a su jugador mas cercano; los
demas sostienen su posicion de formacion. Se ira sumando decision (pase/remate),
marca, coberturas, etc. (ver docs/DESIGN.md seccion 6).

Las funciones son puras: leen el estado y devuelven la velocidad deseada; no
mutan nada (el motor integra).
"""

from ...domain.enums import Position
from ...domain.player import Player
from .entities import MatchPlayer, Side
from .geometry import Vec2
from .state import MatchState

# Velocidad maxima de carrera (m/s) derivada del atributo speed (1-100).
_MIN_SPEED = 3.0
_SPEED_RANGE = 6.0
# Radio (m) dentro del cual el jugador desacelera al acercarse al objetivo.
_SLOW_RADIUS = 2.0
# El arquero se planta esta distancia (m) por delante de su arco.
_GK_GUARD_DEPTH = 3.0
# Margen (m) a cada lado de la boca del arco que el arquero llega a cubrir.
_GK_COVER_MARGIN = 1.0


def max_speed(player: Player) -> float:
    """Velocidad maxima en m/s segun el atributo speed."""
    return _MIN_SPEED + (player.speed / 100.0) * _SPEED_RANGE


def seek(origin: Vec2, target: Vec2, top_speed: float) -> Vec2:
    """Velocidad para ir derecho al objetivo a maxima velocidad."""
    return (target - origin).normalized() * top_speed


def arrive(origin: Vec2, target: Vec2, top_speed: float, slow_radius: float = _SLOW_RADIUS) -> Vec2:
    """Como seek, pero desacelera al entrar al radio para no pasarse."""
    offset = target - origin
    distance = offset.length()
    if distance < 1e-6:
        return Vec2(0.0, 0.0)
    if distance < slow_radius:
        speed = top_speed * (distance / slow_radius)
    else:
        speed = top_speed
    return offset.normalized() * speed


def is_goalkeeper(mp: MatchPlayer) -> bool:
    """Si el jugador es arquero."""
    return mp.player.position is Position.GOALKEEPER


def team_ball_chaser(state: MatchState, side: Side) -> MatchPlayer:
    """El jugador de campo del equipo `side` mas cercano a la pelota.

    Se excluye al arquero: el que persigue por todo el campo es un jugador de
    campo. Si por algun motivo el equipo no tiene jugadores de campo, se usa al
    arquero como ultimo recurso.
    """
    ball = state.ball.position
    outfield = [mp for mp in state.team(side) if not is_goalkeeper(mp)]
    pool = outfield or state.team(side)
    return min(pool, key=lambda mp: mp.position.distance_to(ball))


def team_goalkeeper(state: MatchState, side: Side) -> MatchPlayer | None:
    """El arquero del equipo `side`, o None si la formacion no puso uno."""
    for mp in state.team(side):
        if is_goalkeeper(mp):
            return mp
    return None


def goalkeeper_velocity(mp: MatchPlayer, state: MatchState) -> Vec2:
    """Velocidad del arquero: se planta delante del arco y sigue la y de la pelota.

    No persigue por todo el campo; se mueve sobre una linea corta delante de su
    arco, cubriendo el alto de la boca (mas un margen) segun donde este la pelota.
    """
    pitch = state.pitch
    is_home = mp.team is Side.HOME
    own_goal = pitch.home_goal if is_home else pitch.away_goal
    guard_x = own_goal.x + (_GK_GUARD_DEPTH if is_home else -_GK_GUARD_DEPTH)
    center_y = pitch.width / 2
    half = pitch.goal_width / 2 + _GK_COVER_MARGIN
    ball_y = state.ball.position.y
    y = min(max(ball_y, center_y - half), center_y + half)
    return arrive(mp.position, Vec2(guard_x, y), max_speed(mp.player))


def _other(side: Side) -> Side:
    return Side.AWAY if side is Side.HOME else Side.HOME


def attacking_goal(state: MatchState, side: Side) -> Vec2:
    """Arco al que ataca el equipo `side`."""
    return state.pitch.away_goal if side is Side.HOME else state.pitch.home_goal


def nearest_opponent(mp: MatchPlayer, state: MatchState) -> MatchPlayer:
    """Rival mas cercano a un jugador."""
    rivals = state.team(_other(mp.team))
    return min(rivals, key=lambda o: o.position.distance_to(mp.position))


def best_pass_target(
    owner: MatchPlayer, state: MatchState, max_dist: float
) -> MatchPlayer | None:
    """Mejor companero para pasarle: el mas desmarcado, preferentemente adelante.

    "Desmarcado" = lejos del rival mas cercano. "Adelante" = mas cerca del arco
    rival que el que tiene la pelota. Devuelve None si no hay nadie al alcance.
    """
    goal = attacking_goal(state, owner.team)
    owner_to_goal = owner.position.distance_to(goal)
    rivals = state.team(_other(owner.team))

    def openness(mate: MatchPlayer) -> float:
        return min(
            (o.position.distance_to(mate.position) for o in rivals), default=999.0
        )

    mates = [m for m in state.team(owner.team) if m is not owner]
    in_range = [m for m in mates if m.position.distance_to(owner.position) <= max_dist]
    ahead = [m for m in in_range if m.position.distance_to(goal) < owner_to_goal - 1.0]
    pool = ahead or in_range
    if not pool:
        return None
    return max(pool, key=openness)


# El arbitro sigue la jugada a esta distancia (m) y corre a esta velocidad (m/s).
_REF_FOLLOW_DIST = 12.0
_REF_MAX_SPEED = 6.5


def referee_velocity(ref, state: MatchState) -> Vec2:
    """Velocidad del arbitro: trota hacia la pelota pero la sigue a distancia.

    Si ya esta dentro de la distancia de seguimiento, se queda; si la pelota se
    aleja, se acerca hasta esa distancia (no la alcanza ni la disputa).
    """
    to_ball = state.ball.position - ref.position
    dist = to_ball.length()
    if dist <= _REF_FOLLOW_DIST:
        return Vec2(0.0, 0.0)
    target = state.ball.position - to_ball.normalized() * _REF_FOLLOW_DIST
    return arrive(ref.position, target, _REF_MAX_SPEED)


def decide_velocity(mp: MatchPlayer, state: MatchState, is_chaser: bool) -> Vec2:
    """Velocidad deseada de un jugador en este tick.

    El que persigue va hacia la pelota; el resto vuelve a su ancla de formacion.
    """
    target = state.ball.position if is_chaser else mp.base_position
    return arrive(mp.position, target, max_speed(mp.player))
