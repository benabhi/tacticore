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


# --- Marca / defensa (G2) ---
# Radio de la zona que cubre un defensor: de _ZONE_MIN a _ZONE_MAX segun work_rate.
_ZONE_MIN_R = 8.0
_ZONE_MAX_R = 18.0
# Distancia a la que se planta del rival al marcar: de _MARK_LOOSE (flojo) a
# _MARK_TIGHT (pegado) segun positioning/anticipation.
_MARK_TIGHT = 1.2
_MARK_LOOSE = 3.5


def _lerp(a: float, b: float, t: float) -> float:
    """Interpola entre a y b con t en [0, 1] (acotado)."""
    t = min(max(t, 0.0), 1.0)
    return a + (b - a) * t


def own_goal(state: MatchState, side: Side) -> Vec2:
    """Arco que defiende el equipo `side`."""
    return state.pitch.home_goal if side is Side.HOME else state.pitch.away_goal


def zone_radius(player: Player) -> float:
    """Radio (m) de la zona que cubre el defensor; mas grande con mas work_rate."""
    return _lerp(_ZONE_MIN_R, _ZONE_MAX_R, player.work_rate / 100.0)


def _mark_distance(player: Player) -> float:
    """Distancia (m) a la que marca: mas chica (pegado) con mejor lectura."""
    quality = (player.positioning + player.anticipation) / 200.0
    return _lerp(_MARK_LOOSE, _MARK_TIGHT, quality)


def marking_assignment(defender: MatchPlayer, state: MatchState) -> MatchPlayer | None:
    """A quien marca este defensor (o None = sostener la zona).

    Este es el "seam" tactico: hoy devuelve el default automatico (zonal con
    enganche) = el rival mas peligroso dentro de la zona del defensor. Mas
    adelante, una orden del manager (`SetMarking`) puede fijar una marca manual
    (hombre a hombre, doble marca) y se consultaria aca primero.
    """
    rivals = state.team(_other(defender.team))
    radius = zone_radius(defender.player)
    center = defender.base_position
    in_zone = [o for o in rivals if o.position.distance_to(center) <= radius]
    if not in_zone:
        return None
    goal = own_goal(state, defender.team)
    # El mas peligroso = el rival en zona mas cerca del arco propio.
    return min(in_zone, key=lambda o: o.position.distance_to(goal))


def marking_point(defender: MatchPlayer, mark: MatchPlayer, state: MatchState) -> Vec2:
    """Donde se para el defensor para marcar: del lado del arco (goal-side)."""
    goal = own_goal(state, defender.team)
    dist = _mark_distance(defender.player)
    goal_side = (goal - mark.position).normalized() * dist
    return mark.position + goal_side


def marking_velocity(defender: MatchPlayer, state: MatchState) -> Vec2:
    """Velocidad de un defensor que marca su zona/rival (no es el que presiona)."""
    mark = marking_assignment(defender, state)
    if mark is None:
        return arrive(defender.position, defender.base_position, max_speed(defender.player))
    target = marking_point(defender, mark, state)
    return arrive(defender.position, target, max_speed(defender.player))


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


# --- Desmarques / movimiento off-ball del ataque (G3.x) ---
# Cuanto sube el atacante sin pelota hacia el arco: de _RUN_MIN a _RUN_MAX segun work_rate.
_RUN_MIN_ADVANCE = 4.0
_RUN_MAX_ADVANCE = 14.0
# Si un rival esta mas cerca que esto del punto de desmarque, se busca espacio.
_RUN_SPACE_RADIUS = 4.0
_RUN_SPACE_PUSH = 4.0


def attacking_run_target(mp: MatchPlayer, state: MatchState) -> Vec2:
    """Punto al que se desmarca un atacante sin pelota: adelantado y en espacio.

    Sube desde su ancla hacia el arco rival (mas con mas `work_rate`) y, si tiene
    un rival encima, se corre a un costado para ofrecerse libre.
    """
    goal = attacking_goal(state, mp.team)
    base = mp.base_position
    advance = _lerp(_RUN_MIN_ADVANCE, _RUN_MAX_ADVANCE, mp.player.work_rate / 100.0)
    target = base + (goal - base).normalized() * advance
    rivals = state.team(_other(mp.team))
    if rivals:
        nearest = min(rivals, key=lambda o: o.position.distance_to(target))
        gap = nearest.position.distance_to(target)
        if 1e-6 < gap < _RUN_SPACE_RADIUS:
            target = target + (target - nearest.position).normalized() * _RUN_SPACE_PUSH
    return target


def attacking_run_velocity(mp: MatchPlayer, state: MatchState) -> Vec2:
    """Velocidad de un atacante sin pelota mientras su equipo ataca (desmarque)."""
    return arrive(mp.position, attacking_run_target(mp, state), max_speed(mp.player))


# Hasta esta distancia (m) un pase se considera "corto"; mas alla es "largo".
_SHORT_PASS_RANGE = 18.0


def pick_pass(
    owner: MatchPlayer, state: MatchState, max_dist: float
) -> tuple[MatchPlayer, bool] | None:
    """Elige a quien pasarle y si es pase corto o largo (sin aplicar el error).

    Premia al companero mas desmarcado y mas adelantado. El pase largo es
    atractivo solo si el `owner` tiene `vision` para encontrarlo (si no, juega
    seguro y corto). Devuelve (companero, es_largo) o None si no hay opcion.
    """
    rivals = state.team(_other(owner.team))
    goal = attacking_goal(state, owner.team)
    owner_to_goal = owner.position.distance_to(goal)
    mates = [m for m in state.team(owner.team) if m is not owner]
    in_range = [m for m in mates if m.position.distance_to(owner.position) <= max_dist]
    if not in_range:
        return None

    def openness(m: MatchPlayer) -> float:
        return min((o.position.distance_to(m.position) for o in rivals), default=999.0)

    def score(m: MatchPlayer) -> float:
        s = openness(m)
        if m.position.distance_to(owner.position) > _SHORT_PASS_RANGE:
            # Pase largo: mas riesgoso, solo si el owner lo "ve" (vision).
            s *= 0.5 + 0.5 * (owner.player.vision / 100.0)
        return s

    # Se prioriza progresar: companeros mas cerca del arco rival que el que tiene
    # la pelota; si no hay, se elige entre todos. Entre el pool, el mas desmarcado.
    ahead = [m for m in in_range if m.position.distance_to(goal) < owner_to_goal - 1.0]
    pool = ahead or in_range
    best = max(pool, key=score)
    is_long = best.position.distance_to(owner.position) > _SHORT_PASS_RANGE
    return best, is_long


def is_offside(receiver: MatchPlayer, owner: MatchPlayer, state: MatchState) -> bool:
    """Si `receiver` esta en posicion adelantada al recibir un pase de `owner`.

    Regla simplificada: en campo rival, por delante de la pelota y del
    anteultimo defensor (la "linea de offside"). No considera el momento exacto
    del toque ni pasivos; alcanza para que los desmarques tengan riesgo.
    """
    if receiver is owner:
        return False
    defenders = state.team(_other(owner.team))
    if len(defenders) < 2:
        return False
    mid = state.pitch.length / 2
    rx = receiver.position.x
    ball_x = state.ball.position.x
    if owner.team is Side.HOME:  # ataca hacia +x
        line = sorted((d.position.x for d in defenders), reverse=True)[1]
        return rx > mid and rx > ball_x and rx > line
    line = sorted(d.position.x for d in defenders)[1]  # ataca hacia -x
    return rx < mid and rx < ball_x and rx < line


def decide_velocity(mp: MatchPlayer, state: MatchState, is_chaser: bool) -> Vec2:
    """Velocidad deseada de un jugador en este tick.

    El que persigue va hacia la pelota; el resto vuelve a su ancla de formacion.
    """
    target = state.ball.position if is_chaser else mp.base_position
    return arrive(mp.position, target, max_speed(mp.player))
