"""Loop diario: avanzar un dia procesando TODO el mundo.

La semana tiene eventos fijos (adaptados, no identicos a Hattrick). `advance_day`
avanza el calendario un dia y despacha segun el dia de la semana. Hoy se procesan:

- Viernes: cierre economico (cobra patrocinador, paga sueldos/upkeep/socios; ajusta
  la moral hacia una base influida por el liderazgo del DT).
- Sabado: fecha de liga (resuelve los partidos del dia con el motor estadistico,
  acredita la taquilla al local y paga bonus por racha de victorias).
- Domingo: los socios reaccionan al resultado del sabado.

Lunes a jueves son ganchos para milestones futuros (cantera, copa, recuperacion de
lesionados, entrenamiento) y por ahora no hacen nada. Todo es determinista con un
`random.Random` derivado de la semilla y el dia. Vive en simulation/: no toca la UI.
"""

import random
from datetime import date

from ..core.rng import new_rng
from ..domain.enums import Morale
from .economy import (
    matchday_income, membership_income, squad_wage_bill, stadium_upkeep)
from .facilities import facility_income, tick_constructions
from .match_engine import simulate_match

# Etiqueta del evento de cada dia de la semana (0=lunes .. 6=domingo).
_WEEKDAY_EVENT = {
    0: "Cantera y juveniles",
    1: "Copa y amistosos",
    2: "Recuperacion de lesionados",
    3: "Entrenamiento",
    4: "Cierre economico (cobros y pagos)",
    5: "Fecha de liga",
    6: "Reaccion de los hinchas",
}


def day_event(d: date) -> str:
    """Texto del evento que corresponde a la fecha `d` (por su dia de la semana)."""
    return _WEEKDAY_EVENT[d.weekday()]


def _leagues(game) -> list:
    return [lg for co in game.countries for lg in co.leagues]


def _all_clubs(game) -> list:
    return [c for lg in _leagues(game) for c in lg.clubs]


def advance_day(game, rng: random.Random | None = None, progress=None) -> date:
    """Avanza un dia y procesa el evento de ese dia de la semana. Devuelve la fecha."""
    from .season import ensure_all_fixtures

    ensure_all_fixtures(game)  # que todas las ligas tengan fixture para poder jugar
    game.calendar.advance(1)
    today = game.calendar.current_date
    rng = rng or new_rng(game.seed + today.toordinal())
    # Las obras avanzan todos los dias (hoy solo el jugador tiene obras).
    for club in _all_clubs(game):
        tick_constructions(club)
    wd = today.weekday()
    if wd == 4:
        _weekly_economy(game, today, rng, progress)
    elif wd == 5:
        _play_matchday(game, today, rng, progress)
    elif wd == 6:
        _fans_update(game, rng, progress)
    elif progress is not None:  # dias sin proceso: la barra igual se completa
        progress(day_event(today), 1, 1)
    return today


# --- Viernes: economia semanal ---
def _weekly_economy(game, today: date, rng: random.Random, progress) -> None:
    clubs = _all_clubs(game)
    total = len(clubs) or 1
    label = day_event(today)
    for i, club in enumerate(clubs, start=1):
        income = membership_income(club.members) + facility_income(club)
        spon = club.sponsor
        if spon is not None and spon.active:
            income += spon.weekly_pay
            spon.weeks_remaining -= 1
        expenses = squad_wage_bill(club.players, today) + stadium_upkeep(club.stadium.capacity)
        club.capital += income - expenses
        _drift_morale(club, rng)
        if progress is not None and (i % 50 == 0 or i == total):
            progress(label, i, total)


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
def _play_matchday(game, today: date, rng: random.Random, progress) -> None:
    leagues = _leagues(game)
    total = len(leagues) or 1
    label = day_event(today)
    for i, league in enumerate(leagues, start=1):
        for m in league.matches:
            if m.match_date == today and not m.played:
                res = simulate_match(m.home, m.away, rng)
                m.home_goals, m.away_goals, m.played = res.home_goals, res.away_goals, True
                m.home.capital += matchday_income(m.home, m.away)
                _maybe_streak_bonus(league, m.home)
                _maybe_streak_bonus(league, m.away)
        if progress is not None and (i % 20 == 0 or i == total):
            progress(label, i, total)


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
