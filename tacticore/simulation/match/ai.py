"""IA de los jugadores en el partido (steering minimalista).

B3.1: cada equipo manda a perseguir la pelota a su jugador mas cercano; los
demas sostienen su posicion de formacion. Se ira sumando decision (pase/remate),
marca, coberturas, etc. (ver docs/DESIGN.md seccion 6).

Las funciones son puras: leen el estado y devuelven la velocidad deseada; no
mutan nada (el motor integra).
"""

from ...domain.player import Player
from .entities import MatchPlayer, Side
from .geometry import Vec2
from .state import MatchState

# Velocidad maxima de carrera (m/s) derivada del atributo speed (1-100).
_MIN_SPEED = 3.0
_SPEED_RANGE = 6.0
# Radio (m) dentro del cual el jugador desacelera al acercarse al objetivo.
_SLOW_RADIUS = 2.0


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


def team_ball_chaser(state: MatchState, side: Side) -> MatchPlayer:
    """El jugador del equipo `side` mas cercano a la pelota."""
    ball = state.ball.position
    return min(state.team(side), key=lambda mp: mp.position.distance_to(ball))


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


def decide_velocity(mp: MatchPlayer, state: MatchState, is_chaser: bool) -> Vec2:
    """Velocidad deseada de un jugador en este tick.

    El que persigue va hacia la pelota; el resto vuelve a su ancla de formacion.
    """
    target = state.ball.position if is_chaser else mp.base_position
    return arrive(mp.position, target, max_speed(mp.player))
