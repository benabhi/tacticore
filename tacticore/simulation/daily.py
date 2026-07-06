"""Loop diario: avanzar un dia procesando TODO el mundo.

La semana tiene eventos fijos (adaptados, no identicos a Hattrick). `advance_day`
avanza el calendario un dia y despacha segun el dia de la semana:

- Lunes: los socios reaccionan al resultado de la fecha de liga del domingo.
- Miercoles: mercado de pases (altas/bajas de la IA) y AMISTOSO del club del
  jugador (contra un club del mismo nivel de otro pais).
- Jueves: entrenamiento (por ahora solo deja el resumen como notificacion).
- Viernes: cierre economico (cobra patrocinador, paga sueldos/upkeep/socios;
  ajusta la moral hacia una base influida por el liderazgo del DT).
- Domingo: fecha de liga (resuelve los partidos con el motor estadistico, acredita
  la taquilla al local y paga bonus por racha de victorias).

Martes y sabado son ganchos para milestones futuros (cantera, copa, previa) y por
ahora no hacen nada. Todo es determinista con un `random.Random` derivado de la
semilla y el dia. Deja NOTIFICACIONES para el jugador y anota los MOVIMIENTOS de
caja de su club. Vive en simulation/: no toca la UI.
"""

import random
from datetime import date

from ..core.rng import new_rng
from ..domain.enums import MatchKind, Morale
from .discipline import apply_player_match_discipline, recover_injuries
from .economy import (
    matchday_income, membership_income, squad_wage_bill, stadium_upkeep)
from .facilities import facility_income, tick_constructions
from .finance_log import record_movement
from .formation_training import train_formation
from .match_engine import simulate_match
from . import notifications as notif
from . import staff
from .transfers import ai_market_step, resolve_offers

# Etiqueta del evento de cada dia de la semana (0=lunes .. 6=domingo).
_WEEKDAY_EVENT = {
    0: "Reaccion de los hinchas",
    1: "Dia libre",
    2: "Mercado y amistoso",
    3: "Entrenamiento",
    4: "Cierre economico (cobros y pagos)",
    5: "Previa del partido",
    6: "Fecha de liga",
}

# Version corta para la barra superior (entra en pocos caracteres).
_WEEKDAY_EVENT_SHORT = {
    0: "Hinchas",
    1: "Libre",
    2: "Mercado",
    3: "Entreno",
    4: "Finanzas",
    5: "Previa",
    6: "Liga",
}


def day_event(d: date) -> str:
    """Texto del evento que corresponde a la fecha `d` (por su dia de la semana)."""
    return _WEEKDAY_EVENT[d.weekday()]


def day_event_short(d: date) -> str:
    """Version corta del evento del dia (para la barra superior)."""
    return _WEEKDAY_EVENT_SHORT[d.weekday()]


def player_match_on(game, d: date):
    """Partido pendiente del club del jugador en la fecha `d` (liga o amistoso), o None.

    Sirve para que la UI detecte que ese dia hay que jugar EN VIVO (en vez de
    resolverlo con el motor estadistico como al resto del mundo)."""
    pc = game.player_club
    if pc is None:
        return None
    league = game.player_league
    league_matches = league.matches if league is not None else []
    for m in list(league_matches) + list(game.friendlies):
        if m.match_date == d and not m.played and (m.home is pc or m.away is pc):
            return m
    return None


def _leagues(game) -> list:
    return [lg for co in game.countries for lg in co.leagues]


def _all_clubs(game) -> list:
    return [c for lg in _leagues(game) for c in lg.clubs]


def advance_day(game, rng: random.Random | None = None, progress=None,
                skip_player_match: bool = False) -> date:
    """Avanza un dia y procesa el evento de ese dia de la semana. Devuelve la fecha.

    Si `skip_player_match` y ese dia hay partido de liga del club del jugador, ese
    partido NO se resuelve estadisticamente: queda pendiente para jugarse EN VIVO
    (la UI lo detecta con `player_match_on` y lo cierra con `finish_player_match`).
    """
    from .season import ensure_all_fixtures, ensure_player_friendlies

    ensure_all_fixtures(game)  # que todas las ligas tengan fixture para poder jugar
    ensure_player_friendlies(game)  # amistosos del jugador (miercoles)
    game.calendar.advance(1)
    today = game.calendar.current_date
    rng = rng or new_rng(game.seed + today.toordinal())
    # Las obras avanzan todos los dias (hoy solo el jugador tiene obras).
    for club in _all_clubs(game):
        tick_constructions(club)
    # Altas de lesionados del club del jugador cuya baja ya vencio.
    recover_injuries(game, today)
    # Las ofertas del jugador maduran un dia por vez (el vendedor responde).
    resolve_offers(game)
    wd = today.weekday()
    if wd == 0:  # lunes: los socios reaccionan al partido del domingo
        _fans_update(game, rng, progress)
    elif wd == 2:  # miercoles: mercado + amistoso del jugador
        ai_market_step(game, rng)
        _play_friendly(game, today, rng, skip_player_match)
        if progress is not None:
            progress(day_event(today), 1, 1)
    elif wd == 3:  # jueves: entrenamiento (resumen)
        _training_summary(game)
        if progress is not None:
            progress(day_event(today), 1, 1)
    elif wd == 4:  # viernes: cierre economico
        _weekly_economy(game, today, rng, progress)
    elif wd == 6:  # domingo: fecha de liga
        skip = player_match_on(game, today) if skip_player_match else None
        _play_matchday(game, today, rng, progress, skip=skip)
    elif progress is not None:  # dias sin proceso: la barra igual se completa
        progress(day_event(today), 1, 1)
    # Si se jugo la ultima fecha de todas las ligas, cerrar la temporada
    # (ascensos/descensos + fixture nuevo). Idempotente: solo corre con todo jugado.
    from .promotion import maybe_end_season
    maybe_end_season(game, rng)
    return today


# --- Miercoles: amistoso del club del jugador ---
def _play_friendly(game, today: date, rng: random.Random, skip: bool) -> None:
    """Resuelve el amistoso del jugador (si hoy hay). Con `skip`, lo deja para
    jugarlo EN VIVO desde la UI (como los partidos de liga)."""
    if skip:
        return
    match = player_match_on(game, today)
    if match is None:
        return
    res = simulate_match(match.home, match.away, rng)
    finish_player_match(game, match, res.home_goals, res.away_goals)


# --- Jueves: resumen de entrenamiento (por ahora, solo una notificacion) ---
def _training_summary(game) -> None:
    """Deja el resumen de entrenamiento como notificacion (contenido a futuro)."""
    club = game.player_club
    if club is None or club.coach is None:
        return
    notif.notify(
        game, "Resumen de entrenamiento",
        f"El plantel entreno esta semana bajo {club.coach.full_name}.",
        notif.TRAINING,
    )


# --- Viernes: economia semanal ---
def _weekly_economy(game, today: date, rng: random.Random, progress) -> None:
    clubs = _all_clubs(game)
    total = len(clubs) or 1
    label = day_event(today)
    pc = game.player_club
    for i, club in enumerate(clubs, start=1):
        dues = membership_income(club.members)
        facs = facility_income(club)
        spon = club.sponsor
        spon_pay = 0
        if spon is not None and spon.active:
            spon_pay = spon.weekly_pay
            spon.weeks_remaining -= 1
        wages = squad_wage_bill(club.players, today)
        upkeep = stadium_upkeep(club.stadium.capacity)
        # Cuerpo de trabajo: el director financiero suma ingreso; todos cobran sueldo.
        fin_bonus = round((dues + facs) * staff.finance_income_bonus(club))
        staff_wages = staff.staff_wage_bill(club)
        income = dues + facs + spon_pay + fin_bonus
        expenses = wages + upkeep + staff_wages
        club.capital += income - expenses
        _drift_morale(club, rng)
        if club is pc:  # solo el club del jugador lleva libro y recibe notificacion
            record_movement(club, today, "Cuota de socios", dues)
            record_movement(club, today, "Instalaciones", facs)
            record_movement(club, today, "Patrocinador", spon_pay)
            record_movement(club, today, "Gestion financiera", fin_bonus)
            record_movement(club, today, "Sueldos", -wages)
            record_movement(club, today, "Empleados", -staff_wages)
            record_movement(club, today, "Mantenimiento estadio", -upkeep)
            _notify_weekly_economy(game, club, income - expenses)
        if progress is not None and (i % 50 == 0 or i == total):
            progress(label, i, total)


def _money(amount: int) -> str:
    """Formatea un monto como '$1.234' (para el texto de las notificaciones)."""
    return "$" + f"{amount:,}".replace(",", ".")


def _notify_weekly_economy(game, club, net: int) -> None:
    """Notifica el cierre economico de la semana (resultado + caja)."""
    sign = "+" if net >= 0 else "-"
    notif.notify(
        game, "Cierre economico",
        f"Resultado de la semana: {sign}{_money(abs(net))}. "
        f"Caja: {_money(club.capital)}.",
        notif.FINANCE,
    )


def _drift_morale(club, rng: random.Random) -> None:
    """La moral del plantel deriva hacia una base fijada por el liderazgo del DT."""
    if not club.players:
        return
    lead = club.coach.leadership if club.coach else 50.0
    target = 4 if lead >= 65 else 3 if lead >= 40 else 2
    for p in club.players:
        v = p.morale.value
        if v < target and rng.random() < 0.5:
            p.morale = Morale(v + 1)
        elif v > target and rng.random() < 0.3:
            p.morale = Morale(v - 1)


# --- Sabado: fecha de liga ---
def _play_matchday(game, today: date, rng: random.Random, progress, skip=None) -> None:
    """Resuelve todos los partidos del dia con el motor estadistico.

    `skip` es un partido que NO se resuelve aca (lo juega el jugador en vivo y lo
    cierra `finish_player_match`)."""
    leagues = _leagues(game)
    total = len(leagues) or 1
    label = day_event(today)
    pc = game.player_club
    for i, league in enumerate(leagues, start=1):
        for m in league.matches:
            if m is skip:
                continue
            if m.match_date == today and not m.played:
                res = simulate_match(m.home, m.away, rng)
                if pc in (m.home, m.away):
                    # El partido del jugador (caso headless, no en vivo) pasa por el
                    # mismo cierre que en vivo: taquilla, racha, entreno y disciplina.
                    finish_player_match(game, m, res.home_goals, res.away_goals, rng)
                    continue
                m.home_goals, m.away_goals, m.played = res.home_goals, res.away_goals, True
                _credit_matchday_income(game, m, today)
                _maybe_streak_bonus(league, m.home)
                _maybe_streak_bonus(league, m.away)
        if progress is not None and (i % 20 == 0 or i == total):
            progress(label, i, total)


def _credit_matchday_income(game, match, when: date) -> int:
    """Acredita la taquilla al local. Si el local es el club del jugador, lo anota
    como movimiento (economia en tiempo real). Devuelve el monto."""
    gate = matchday_income(match.home, match.away)
    match.home.capital += gate
    if match.home is game.player_club:
        record_movement(match.home, when, f"Taquilla vs {match.away.name}", gate)
    return gate


def finish_player_match(game, match, home_goals: int, away_goals: int,
                        rng: random.Random | None = None) -> None:
    """Registra el resultado de un partido que juega el club del jugador.

    Aplica taquilla al local (en tiempo real), bonus de racha del patrocinador
    (solo en LIGA), entrenamiento de la formacion desplegada, la DISCIPLINA
    (suspensiones, tarjetas, lesiones del once que jugo) y una notificacion con el
    resultado. Los hinchas reaccionan el lunes, como siempre."""
    match.home_goals = home_goals
    match.away_goals = away_goals
    match.played = True
    when = game.calendar.current_date
    rng = rng or new_rng(game.seed + when.toordinal())
    _credit_matchday_income(game, match, when)
    league = game.player_league
    # El bonus por racha es de competencia: no aplica en amistosos.
    if league is not None and match.kind is MatchKind.LEAGUE:
        _maybe_streak_bonus(league, match.home)
        _maybe_streak_bonus(league, match.away)
    pc = game.player_club
    if pc in (match.home, match.away) and match.tactic is not None:
        train_formation(pc, match.tactic.formation, pc.coach)
    apply_player_match_discipline(game, match, when, rng)
    _notify_result(game, match)


def _notify_result(game, match) -> None:
    """Notifica el resultado del partido del jugador (con G/E/P desde su lado)."""
    pc = game.player_club
    if pc not in (match.home, match.away):
        return
    gf = match.home_goals if match.home is pc else match.away_goals
    ga = match.away_goals if match.home is pc else match.home_goals
    outcome = "Victoria" if gf > ga else "Derrota" if gf < ga else "Empate"
    notif.notify(
        game, f"{outcome} ({match.kind.value})",
        f"{match.home.name} {match.home_goals}-{match.away_goals} {match.away.name}.",
        notif.MATCH,
    )


def _win_streak(league, club) -> int:
    """Victorias consecutivas del club (desde su ultimo partido jugado hacia atras)."""
    played = sorted(
        (m for m in league.matches if m.played and (m.home is club or m.away is club)),
        key=lambda m: m.matchday, reverse=True,
    )
    streak = 0
    for m in played:
        won = ((m.home is club and m.home_goals > m.away_goals)
               or (m.away is club and m.away_goals > m.home_goals))
        if won:
            streak += 1
        else:
            break
    return streak


def _maybe_streak_bonus(league, club) -> None:
    """Paga el bonus del patrocinador si el club acaba de completar una racha."""
    spon = club.sponsor
    if spon is None or spon.streak_len <= 0 or spon.streak_bonus <= 0:
        return
    streak = _win_streak(league, club)
    if streak > 0 and streak % spon.streak_len == 0:
        club.capital += spon.streak_bonus


# --- Domingo: reaccion de los hinchas ---
def _last_played(league, club):
    played = [m for m in league.matches
              if m.played and (m.home is club or m.away is club)]
    return max(played, key=lambda m: m.matchday) if played else None


def _fans_update(game, rng: random.Random, progress) -> None:
    leagues = _leagues(game)
    total = len(leagues) or 1
    label = _WEEKDAY_EVENT[6]
    for i, league in enumerate(leagues, start=1):
        for club in league.clubs:
            m = _last_played(league, club)
            if m is None:
                continue
            gf = m.home_goals if m.home is club else m.away_goals
            ga = m.away_goals if m.home is club else m.home_goals
            if gf > ga:  # gano: crece la masa societaria
                club.members = round(club.members * 1.01) + rng.randint(0, 15)
            elif gf < ga:  # perdio: se estanca o baja un poco
                club.members = max(200, round(club.members * 0.995))
            else:
                club.members += rng.randint(0, 5)
        if progress is not None and (i % 20 == 0 or i == total):
            progress(label, i, total)
