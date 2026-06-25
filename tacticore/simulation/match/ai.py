"""IA de los jugadores en el partido (steering minimalista).

B3.1: cada equipo manda a perseguir la pelota a su jugador mas cercano; los
demas sostienen su posicion de formacion. Se ira sumando decision (pase/remate),
marca, coberturas, etc. (ver docs/DESIGN.md seccion 6).

Las funciones son puras: leen el estado y devuelven la velocidad deseada; no
mutan nada (el motor integra).
"""

from ...domain.player import Player
from .entities import MatchPlayer, Role, Side
from .geometry import Vec2
from .state import MatchState

# Velocidad maxima de carrera (m/s) derivada del atributo speed (1-100).
_MIN_SPEED = 3.0
_SPEED_RANGE = 6.0
# Radio (m) dentro del cual el jugador desacelera al acercarse al objetivo.
_SLOW_RADIUS = 2.0
# El arquero se planta entre esta distancia (defendiendo, sobre la linea) y
# _GK_SWEEP_DEPTH (atacando su equipo, sale a hacer de libero hacia el area grande).
_GK_GUARD_DEPTH = 3.0
_GK_SWEEP_DEPTH = 14.0
# Margen (m) a cada lado de la boca del arco que el arquero llega a cubrir.
_GK_COVER_MARGIN = 1.0
# Pelota suelta mas lenta que esto, dentro del area -> el arquero sale a asegurarla.
_GK_CLAIM_SPEED = 12.0


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
    """Si el jugador juega de arquero (por su rol en la formacion)."""
    return mp.role is Role.GOALKEEPER


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


def goalkeeper_short_option(
    gk: MatchPlayer, state: MatchState, max_dist: float = 25.0
) -> MatchPlayer | None:
    """Companero cercano y bien libre para que el arquero saque corto (o None)."""
    rivals = state.team(_other(gk.team))
    mates = [
        m
        for m in state.team(gk.team)
        if m is not gk and m.position.distance_to(gk.position) <= max_dist
    ]
    if not mates:
        return None

    def openness(m: MatchPlayer) -> float:
        return min((o.position.distance_to(m.position) for o in rivals), default=999.0)

    best = max(mates, key=openness)
    return best if openness(best) > 5.0 else None  # solo si esta claramente libre


def goalkeeper_carry_velocity(gk: MatchPlayer, state: MatchState) -> Vec2:
    """El arquero camina (despacio) dentro de su area buscando a quien pasarle.

    Va hacia el lado del companero libre mas conveniente (o hacia el frente de su
    area si no hay), siempre acotado al area grande (no sale de ahi).
    """
    pitch = state.pitch
    is_home = gk.team is Side.HOME
    area = pitch.penalty_area(is_home)
    short = goalkeeper_short_option(gk, state, max_dist=45.0)
    if short is not None:
        offset = short.position - gk.position
        step = offset.normalized() * 6.0 if offset.length() > 1e-6 else offset
        target = gk.position + step
    else:
        front_x = area.max_x if is_home else area.x
        target = Vec2(front_x, gk.position.y)
    target = area.clamp(target)  # nunca se sale del area grande
    return arrive(gk.position, target, max_speed(gk.player) * 0.6)  # camina, no corre


def goalkeeper_velocity(mp: MatchPlayer, state: MatchState) -> Vec2:
    """Velocidad del arquero: se planta delante del arco y sigue la y de la pelota.

    No persigue por todo el campo; se mueve sobre una linea corta delante de su
    arco, cubriendo el alto de la boca (mas un margen) segun donde este la pelota.
    """
    pitch = state.pitch
    is_home = mp.team is Side.HOME
    own_goal = pitch.home_goal if is_home else pitch.away_goal
    ball = state.ball.position
    # Pelota suelta y lenta dentro de su area: SALE a asegurarla (la barre).
    area = pitch.penalty_area(is_home)
    if (
        state.ball.owner is None
        and area.contains(ball)
        and state.ball.velocity.length() < _GK_CLAIM_SPEED
    ):
        return arrive(mp.position, ball, max_speed(mp.player))
    # Sube mas cuanto mas lejos esta la pelota del arco propio (equipo atacando):
    # de la linea (_GK_GUARD_DEPTH) al borde del area grande (_GK_SWEEP_DEPTH).
    dist_to_own = ball.x if is_home else (pitch.length - ball.x)
    frac = min(max(dist_to_own / pitch.length, 0.0), 1.0)
    depth = _lerp(_GK_GUARD_DEPTH, _GK_SWEEP_DEPTH, frac)
    guard_x = own_goal.x + (depth if is_home else -depth)
    center_y = pitch.width / 2
    half = pitch.goal_width / 2 + _GK_COVER_MARGIN
    y = min(max(ball.y, center_y - half), center_y + half)
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
    in_range = [
        m for m in mates
        if m.position.distance_to(owner.position) <= max_dist
        and not is_offside(m, owner, state)  # no pasar a un companero adelantado
    ]
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


def defensive_line_x(state: MatchState, side: Side) -> float:
    """Coordenada x de la linea defensiva de `side`: ACOMPANA al atacante mas
    adelantado (se para un pelin goal-side para mantenerlo en juego). Asi la
    ultima linea sube y baja con el ataque -> los delanteros quedan habilitados y
    se juega en el area; el offside queda para cuando los pasan/contras.

    Acotada: ni dentro del arco chico ni pasada de mitad de cancha.
    """
    pitch = state.pitch
    attackers = state.team(_other(side))
    if side is Side.HOME:  # defiende x = 0
        deepest = min((a.position.x for a in attackers), default=pitch.length)
        return min(max(deepest - 2.0, 14.0), pitch.length * 0.55)
    deepest = max((a.position.x for a in attackers), default=0.0)  # defiende x = length
    return max(min(deepest + 2.0, pitch.length - 14.0), pitch.length * 0.45)


def marking_velocity(defender: MatchPlayer, state: MatchState) -> Vec2:
    """Velocidad de un defensor que marca (no es el que presiona).

    La **ultima linea** (centrales y laterales) sostiene una **linea compacta**
    que acompana al atacante mas adelantado (`defensive_line_x`), cubriendo cada
    uno su franja; el resto marca a su rival goal-side.
    """
    mark = marking_assignment(defender, state)
    if mark is not None:
        # Marca activa: se planta goal-side del rival y lo acompana (lo sigue
        # aunque se mueva), no se queda parado en la linea.
        target = marking_point(defender, mark, state)
    elif defender.role in (Role.CENTER_BACK, Role.FULLBACK):
        # Sin rival a quien marcar: la ultima linea sostiene su altura compacta.
        target = Vec2(defensive_line_x(state, defender.team), defender.base_position.y)
    else:
        target = defender.base_position
    return arrive(defender.position, target, max_speed(defender.player))


# El arbitro sigue la jugada a esta distancia (m) y corre a esta velocidad (m/s).
_REF_FOLLOW_DIST = 12.0
_REF_MIN_DIST = 7.0   # nunca mas cerca que esto: no tapa el juego (ej. saque del medio)
_REF_MAX_SPEED = 6.5


def referee_velocity(ref, state: MatchState) -> Vec2:
    """Velocidad del arbitro: trota cerca de la jugada pero sin taparla.

    Mantiene una banda de distancia: si la pelota se aleja, se acerca hasta
    `_REF_FOLLOW_DIST`; si le queda **demasiado encima** (saque del medio, balon
    parado), se corre al costado hasta `_REF_MIN_DIST` para no tapar al que juega.
    """
    to_ball = state.ball.position - ref.position
    dist = to_ball.length()
    if dist < _REF_MIN_DIST:
        # Demasiado cerca: se aparta (si esta justo encima, hacia un costado fijo).
        away = (to_ball * -1.0).normalized() if dist > 1e-6 else Vec2(0.0, 1.0)
        target = state.ball.position + away * _REF_FOLLOW_DIST
        return arrive(ref.position, target, _REF_MAX_SPEED)
    if dist <= _REF_FOLLOW_DIST:
        return Vec2(0.0, 0.0)
    target = state.ball.position - to_ball.normalized() * _REF_FOLLOW_DIST
    return arrive(ref.position, target, _REF_MAX_SPEED)


# --- Desmarques / movimiento off-ball del ataque (G3.x) ---
# Cuanto sube el atacante sin pelota hacia el arco: de _RUN_MIN a _RUN_MAX segun work_rate.
_RUN_MIN_ADVANCE = 4.0
_RUN_MAX_ADVANCE = 14.0
# Cuanto sube cada ROL en ataque. Extremos y laterales suben POR LA BANDA
# (mantienen el ancho); volantes y centrales avanzan hacia el arco. El punta se
# maneja aparte (aguanta la linea de offside / crashea el area).
_RUN_LINE_FACTOR = {
    Role.WINGER: 1.5,
    Role.FULLBACK: 1.0,
    Role.MIDFIELDER: 1.1,
    Role.CENTER_BACK: 0.6,
    Role.GOALKEEPER: 0.0,
}
# Si un rival esta mas cerca que esto del punto de desmarque, se busca espacio.
_RUN_SPACE_RADIUS = 4.0
_RUN_SPACE_PUSH = 4.0


def offside_line_x(state: MatchState, attacking_side: Side) -> float | None:
    """Coordenada x de la linea de offside (el anteultimo defensor rival)."""
    defenders = state.team(_other(attacking_side))
    if len(defenders) < 2:
        return None
    xs = [d.position.x for d in defenders]
    if attacking_side is Side.HOME:  # ataca hacia +x: el 2do mas adelantado
        return sorted(xs, reverse=True)[1]
    return sorted(xs)[1]


# Centro inminente: la pelota esta abierta (cerca de una banda) y profunda
# (ultimo tramo del campo rival). Cuando pasa, los de adentro crashean el area.
_CROSS_WIDE_Y = 18.0     # a menos de esto de una banda, la pelota esta "abierta"
_CROSS_DEPTH = 0.32      # fraccion del largo desde la linea de fondo: anticipa el centro
_BOX_SPREAD = 10.0       # cuanto se abren los que llegan al area (primer/segundo palo)


def cross_imminent(state: MatchState, attacking_side: Side) -> bool:
    """Si la pelota esta abierta y profunda en campo rival: se viene un centro."""
    ball = state.ball.position
    pitch = state.pitch
    goal = attacking_goal(state, attacking_side)
    wide = ball.y < _CROSS_WIDE_Y or ball.y > pitch.width - _CROSS_WIDE_Y
    deep = abs(goal.x - ball.x) < pitch.length * _CROSS_DEPTH  # cerca de la linea de fondo
    return wide and deep


def box_crash_target(mp: MatchPlayer, state: MatchState) -> Vec2:
    """Punto DENTRO del area al que llega un atacante a esperar el centro.

    Se abren entre primer y segundo palo segun su franja, a la altura del punto
    penal. No se limita por la linea de offside: el centro se patea a un punto (no
    dispara la regla del offside) y, como en un partido real, los que llegan se
    meten al area a la espera del cabezazo aunque queden algo adelantados.
    """
    pitch = state.pitch
    spot = pitch.penalty_spot(home=(mp.team is Side.AWAY))  # area que ataca
    bias = -1.0 if mp.base_position.y < pitch.width / 2 else 1.0
    ty = min(max(pitch.width / 2 + bias * _BOX_SPREAD, 16.0), pitch.width - 16.0)
    return Vec2(spot.x, ty)


def box_crash_velocity(mp: MatchPlayer, state: MatchState) -> Vec2:
    """Velocidad del que llega al area a esperar/rematar el centro."""
    return arrive(mp.position, box_crash_target(mp, state), max_speed(mp.player))


def attacking_run_target(mp: MatchPlayer, state: MatchState) -> Vec2:
    """Punto al que se desmarca un atacante sin pelota: adelantado y en espacio.

    Si **se viene un centro** (pelota abierta y profunda), los atacantes centrales
    crashean el area a esperar el cabezazo. Si no, los delanteros **aguantan la
    linea de offside**, los extremos/laterales suben **por la banda** y el resto
    sube una fraccion de su zona segun `work_rate` y su linea (`_RUN_LINE_FACTOR`).
    Si tiene un rival encima, se corre a un costado para ofrecerse libre.
    """
    goal = attacking_goal(state, mp.team)
    base = mp.base_position
    pitch = state.pitch
    toward = 1.0 if mp.team is Side.HOME else -1.0  # signo hacia el arco rival (en x)
    line = offside_line_x(state, mp.team)

    # Viene el centro -> los de adentro (punta, volantes, extremo lejano) crashean
    # el area (el que centra tiene la pelota, no pasa por aca).
    if cross_imminent(state, mp.team) and mp.role in (
        Role.STRIKER, Role.MIDFIELDER, Role.WINGER
    ):
        return box_crash_target(mp, state)

    def onside(tx: float) -> float:
        # No pasar la linea de offside (queda 0.8m detras) ni quedar atras de su zona.
        if line is not None:
            tx = min(tx, line - 0.8) if toward > 0 else max(tx, line + 0.8)
        return max(tx, base.x) if toward > 0 else min(tx, base.x)

    if mp.role is Role.STRIKER:
        # Empuja al area cuando el equipo ataca (pelota en campo rival); si no,
        # mantiene su zona alta. La linea rival lo acompana -> queda habilitado.
        ball_x = state.ball.position.x
        attacking = ball_x > pitch.length / 2 if toward > 0 else ball_x < pitch.length / 2
        tx = goal.x - toward * 12.0 if attacking else base.x
        target = Vec2(onside(tx), _lerp(base.y, pitch.width / 2, 0.5))
    elif mp.role in (Role.WINGER, Role.FULLBACK):
        # Sube POR LA BANDA manteniendo el ancho (la y de su zona), siempre onside.
        factor = _RUN_LINE_FACTOR[mp.role]
        advance = _lerp(_RUN_MIN_ADVANCE, _RUN_MAX_ADVANCE, mp.player.work_rate / 100.0) * factor
        target = Vec2(onside(base.x + toward * advance), base.y)
    elif mp.role is Role.CENTER_BACK:
        # El central se DESCARGA por su franja: sube a apoyar la salida en x SIN
        # cerrarse al centro (mantiene su y para abrir angulos de pase, en vez de
        # amontonarse en el eje). Asi ofrece salida sin abandonar la ultima linea.
        factor = _RUN_LINE_FACTOR[mp.role]
        advance = _lerp(_RUN_MIN_ADVANCE, _RUN_MAX_ADVANCE, mp.player.work_rate / 100.0) * factor
        target = Vec2(onside(base.x + toward * advance), base.y)
    else:
        # Volantes y centrales: avanzan hacia el arco (en diagonal a su zona).
        factor = _RUN_LINE_FACTOR.get(mp.role, 1.0)
        advance = _lerp(_RUN_MIN_ADVANCE, _RUN_MAX_ADVANCE, mp.player.work_rate / 100.0) * factor
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


def support_run_velocity(mp: MatchPlayer, state: MatchState) -> Vec2:
    """Carrera de apoyo del que acaba de pasar: pica hacia adelante (onside) para
    ofrecerse a la devolucion (pared / te paso y voy)."""
    line = offside_line_x(state, mp.team)
    toward = 1.0 if mp.team is Side.HOME else -1.0
    tx = mp.position.x + toward * 12.0
    if line is not None:
        tx = min(tx, line - 0.8) if toward > 0 else max(tx, line + 0.8)
    return arrive(mp.position, Vec2(tx, mp.position.y), max_speed(mp.player))


# Hasta esta distancia (m) un pase se considera "corto"; mas alla es "largo".
_SHORT_PASS_RANGE = 18.0
_INTERCEPT_RADIUS = 2.3  # un rival a menos de esto de la linea del pase lo intercepta


def pass_lane_blocked(owner: MatchPlayer, mate: MatchPlayer, rivals) -> bool:
    """Si un rival esta sobre la linea del pase y lo cortaria facil.

    Mira si algun rival cae cerca del segmento owner->mate (entre los dos, no
    detras del pasador ni ya pegado al receptor). Evita pases 'regalados' a un
    companero que tiene un contrario adelante.
    """
    start = owner.position
    seg = mate.position - start
    length = seg.length()
    if length < 1e-6:
        return False
    d = seg.normalized()
    for o in rivals:
        rel = o.position - start
        t = rel.dot(d)
        if t <= 1.5 or t >= length - 1.0:
            continue
        perp = (rel - d * t).length()
        if perp < _INTERCEPT_RADIUS:
            return True
    return False


def _retreating(mate: MatchPlayer, goal: Vec2) -> bool:
    """Si el companero se esta yendo del arco rival (en retroceso): no asistirle ahi."""
    v = mate.velocity
    to_goal = goal - mate.position
    if v.length() < 0.5 or to_goal.length() < 1e-6:
        return False
    return v.dot(to_goal.normalized()) < -1.5  # retrocede a mas de 1.5 m/s


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
    # Descarta companeros con la linea de pase tapada por un rival (interceptable);
    # si TODAS estan tapadas (presion total) se suelta igual con lo que haya.
    clear = [m for m in in_range if not pass_lane_blocked(owner, m, rivals)]
    usable = clear or in_range

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
    ahead = [m for m in usable if m.position.distance_to(goal) < owner_to_goal - 1.0]
    pool = ahead or usable
    best = max(pool, key=score)
    is_long = best.position.distance_to(owner.position) > _SHORT_PASS_RANGE
    return best, is_long


# Alcance de remate: de _SHOOT_MIN (mal tirador) a _SHOOT_MAX (elite) segun shooting.
_SHOOT_MIN_RANGE = 12.0
_SHOOT_MAX_RANGE = 30.0


def shoot_range(player: Player) -> float:
    """Distancia (m) desde la que el jugador se anima a rematar (mas con mas shooting).

    Asi un mal definidor no patea de cualquier lado: gambetea para acercarse al
    arco antes de rematar.
    """
    return _lerp(_SHOOT_MIN_RANGE, _SHOOT_MAX_RANGE, player.shooting / 100.0)


def is_long_pass(owner: MatchPlayer, mate: MatchPlayer) -> bool:
    """Si el pase entre dos jugadores cuenta como largo."""
    return owner.position.distance_to(mate.position) > _SHORT_PASS_RANGE


def better_finisher(
    owner: MatchPlayer, state: MatchState, max_dist: float
) -> MatchPlayer | None:
    """Companero claramente mejor ubicado para definir: mas cerca del arco y libre.

    Es la "jugada con un companero": en vez de rematar/gambetear, buscar el pase
    de gol al que esta mejor parado. Devuelve None si no hay una opcion clara.
    """
    goal = attacking_goal(state, owner.team)
    owner_to_goal = owner.position.distance_to(goal)
    rivals = state.team(_other(owner.team))
    best: MatchPlayer | None = None
    best_open = 4.0  # espacio minimo para que valga la pena el pase
    for mate in state.team(owner.team):
        if mate is owner or mate.position.distance_to(owner.position) > max_dist:
            continue
        if is_offside(mate, owner, state):  # no asistir a un companero adelantado
            continue
        if _retreating(mate, goal):  # no tirar la diagonal al que va en retroceso
            continue
        if pass_lane_blocked(owner, mate, rivals):  # con un rival adelante, no
            continue
        mate_to_goal = mate.position.distance_to(goal)
        # Debe estar mas cerca del arco y en posicion de remate.
        if mate_to_goal > owner_to_goal - 4.0 or mate_to_goal > _SHOOT_MAX_RANGE:
            continue
        openness = min(
            (o.position.distance_to(mate.position) for o in rivals), default=999.0
        )
        if openness > best_open:
            best, best_open = mate, openness
    return best


def open_outlet(owner: MatchPlayer, state: MatchState, max_dist: float) -> MatchPlayer | None:
    """Companero bien desmarcado para CAMBIAR el juego (lateral o en diagonal).

    Sirve para mover el balon a otra zona cuando alguien quedo muy solo, sin
    perder el hilo de ataque: solo considera companeros que NO esten mas atras
    que el que tiene la pelota (evita el toque para atras eterno). None si no hay
    una opcion claramente libre y a una distancia que valga el cambio.
    """
    goal = attacking_goal(state, owner.team)
    owner_to_goal = owner.position.distance_to(goal)
    rivals = state.team(_other(owner.team))
    mates = [
        m
        for m in state.team(owner.team)
        if m is not owner
        and m.position.distance_to(owner.position) <= max_dist
        and m.position.distance_to(goal) <= owner_to_goal + 1.0  # no para atras
        and m.position.distance_to(owner.position) > 12.0        # a otra zona
        and not pass_lane_blocked(owner, m, rivals)              # lane libre
    ]
    if not mates:
        return None

    def openness(m: MatchPlayer) -> float:
        return min((o.position.distance_to(m.position) for o in rivals), default=999.0)

    best = max(mates, key=openness)
    return best if openness(best) > 10.0 else None  # bien solo (no marcado)


def open_winger(owner: MatchPlayer, state: MatchState, max_dist: float) -> MatchPlayer | None:
    """Extremo del equipo, abierto y no atrasado, para abrir el juego a la banda."""
    goal = attacking_goal(state, owner.team)
    owner_to_goal = owner.position.distance_to(goal)
    rivals = state.team(_other(owner.team))
    wingers = [
        m
        for m in state.team(owner.team)
        if m.role is Role.WINGER
        and m is not owner
        and m.position.distance_to(owner.position) <= max_dist
        and m.position.distance_to(goal) <= owner_to_goal + 6.0  # no muy atras
        and not is_offside(m, owner, state)
        and not pass_lane_blocked(owner, m, rivals)
    ]
    if not wingers:
        return None

    def openness(m: MatchPlayer) -> float:
        return min((o.position.distance_to(m.position) for o in rivals), default=999.0)

    best = max(wingers, key=openness)
    return best if openness(best) > 6.0 else None


def is_offside(receiver: MatchPlayer, owner: MatchPlayer, state: MatchState) -> bool:
    """Si `receiver` esta en posicion adelantada al recibir un pase de `owner`.

    Regla simplificada: en campo rival, por delante de la pelota y del
    anteultimo defensor (la "linea de offside"). No considera el momento exacto
    del toque ni pasivos; alcanza para que los desmarques tengan riesgo.
    """
    if receiver is owner:
        return False
    line = offside_line_x(state, owner.team)
    if line is None:
        return False
    mid = state.pitch.length / 2
    rx = receiver.position.x
    ball_x = state.ball.position.x
    if owner.team is Side.HOME:  # ataca hacia +x
        return rx > mid and rx > ball_x and rx > line
    return rx < mid and rx < ball_x and rx < line


def decide_velocity(mp: MatchPlayer, state: MatchState, is_chaser: bool) -> Vec2:
    """Velocidad deseada de un jugador en este tick.

    El que persigue va hacia la pelota; el resto vuelve a su ancla de formacion.
    """
    target = state.ball.position if is_chaser else mp.base_position
    return arrive(mp.position, target, max_speed(mp.player))
