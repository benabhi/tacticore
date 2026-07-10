"""Cantera: los ojeadores descubren juveniles (camadas, revelado, fichar/descartar).

Dos veces por temporada (calendario fijo, ancladas al fixture de la liga del
jugador) cada Cazatalentos contratado trae UN juvenil (`Prospect`). El manager
revisa el informe (descubre las caracteristicas que el ojeador pudo evaluar; mas
cuanto mejor es el ojeador) y decide fichar (pasa al plantel) o descartar. Un
prospecto sin decidir caduca. Logica pura (sin UI); determinista con la semilla.
"""

import random
from datetime import date, timedelta

from ..core.rng import new_rng
from ..domain.enums import BonusType, EmployeeRole
from ..domain.player import ALL_ATTRS
from ..domain.positions import POSITION_PRIORITIES
from ..domain.prospect import Prospect
from ..generators.player_generator import PlayerGenerator
from . import facilities as fac
from . import notifications as notif
from . import staff
from .transfers import MAX_SQUAD

# Dos camadas por temporada, ancladas a la fecha de estas jornadas del fixture
# (aprox. a un tercio y a dos tercios de la temporada de 14 fechas).
_INTAKE_MATCHDAYS = (4, 10)
_PROSPECT_TTL_WEEKS = 8   # cuanto queda un prospecto disponible sin decidir


# --- Fechas de camada (calendario fijo) ---
def _season_anchor(game) -> date | None:
    """Fecha de la 1a jornada de la liga del jugador (ancla de la temporada)."""
    league = game.player_league
    if league is None:
        return None
    dates = [m.match_date for m in league.matches if m.match_date is not None]
    return min(dates) if dates else None


def intake_dates(game) -> list[date]:
    """Las 2 fechas de camada de la temporada actual (martes de esas semanas)."""
    anchor = _season_anchor(game)
    if anchor is None:
        return []
    # anchor es un domingo (fecha de la jornada 1); la camada cae el martes de la
    # semana de cada jornada objetivo.
    return [anchor + timedelta(weeks=k - 1, days=2) for k in _INTAKE_MATCHDAYS]


def next_intake(game, today: date) -> date | None:
    """La proxima fecha de camada estrictamente posterior a `today` (o None)."""
    return next((d for d in intake_dates(game) if d > today), None)


# --- Estado de cantera ---
def scouts(club) -> list:
    """Cazatalentos contratados por el club."""
    return staff.employees_of(club, EmployeeRole.SCOUT)


def has_academy(club) -> bool:
    """True si el club puede ojear (tiene Complejo juvenil construido)."""
    return fac.level(club, "youth") > 0


def _scout_skill(scout) -> float:
    return scout.bonuses.get(BonusType.SCOUTING, 50.0)


# --- Camada (corre en el loop diario) ---
def run_intake(game, today: date, rng: random.Random | None = None) -> None:
    """Poda vencidos y, si hoy es fecha de camada, cada ojeador trae un juvenil."""
    club = game.player_club
    if club is None:
        return
    _prune_expired(club, today)
    if today not in intake_dates(game):
        return
    sc = scouts(club)
    if not sc:
        return
    qbonus = fac.youth_quality_bonus(club)
    expires = today + timedelta(weeks=_PROSPECT_TTL_WEEKS)
    for i, scout in enumerate(sc):
        skill = _scout_skill(scout)
        gen = PlayerGenerator(new_rng(game.seed + today.toordinal() * 7 + i * 101))
        player = gen.generate_youth(club.tier, skill, club.country_code, today,
                                    quality_bonus=qbonus)
        club.prospects.append(Prospect(player, skill, today, expires))
    notif.notify(
        game, "Nueva camada de juveniles",
        f"Tus ojeadores trajeron {len(sc)} juvenil(es). Revisalos en "
        f"Jugadores > Cantera antes de que se vayan.", notif.SQUAD)


def _prune_expired(club, today: date) -> None:
    club.prospects[:] = [p for p in club.prospects if p.expires > today]


# --- Revelado (el informe se descubre segun la calidad del ojeador) ---
def reveal_count(scout_skill: float) -> int:
    """Cuantos atributos ve el manager al revisar (mas, cuanto mejor el ojeador)."""
    if scout_skill < 40:
        return 4
    if scout_skill < 60:
        return 7
    if scout_skill < 80:
        return 10
    return len(ALL_ATTRS)


def revealed_attrs(prospect: Prospect) -> list[str]:
    """Atributos que el ojeador pudo evaluar (incluye siempre el destacado).

    Determinista (mismo prospecto -> mismo set), asi el informe es estable."""
    n = reveal_count(prospect.scout_skill)
    standout = POSITION_PRIORITIES[prospect.player.position][0]
    rest = [a for a in ALL_ATTRS if a != standout]
    seed = prospect.found_date.toordinal() * 131 + sum(ord(c) for c in prospect.player.full_name)
    random.Random(seed).shuffle(rest)
    return [standout] + rest[:max(0, n - 1)]


def standout_attr(prospect: Prospect) -> str:
    """El atributo destacado del juvenil (prioritario de su posicion)."""
    return POSITION_PRIORITIES[prospect.player.position][0]


def potential_stars(prospect: Prospect) -> str:
    """Estimacion del potencial en 5 estrellas ASCII (rough; '*' llenas, '-' vacias)."""
    pot = prospect.player.potential
    stars = max(1, min(5, round((pot - 30) / (95 - 30) * 5)))
    return "*" * stars + "-" * (5 - stars)


# --- Decisiones ---
def reveal(prospect: Prospect) -> None:
    """Marca el informe como revisado (el manager descubrio los datos)."""
    prospect.revealed = True


def sign(game, prospect: Prospect) -> bool:
    """Ficha al juvenil: pasa al plantel (si hay lugar). Gratis. Devuelve si se concreto."""
    club = game.player_club
    if club is None or prospect not in club.prospects:
        return False
    if len(club.players) >= MAX_SQUAD:
        return False
    club.prospects.remove(prospect)
    player = prospect.player
    player.shirt_number = _free_shirt(club)
    club.players.append(player)
    return True


def discard(game, prospect: Prospect) -> None:
    """Descarta al juvenil (el ojeador lo suelta)."""
    club = game.player_club
    if club is not None and prospect in club.prospects:
        club.prospects.remove(prospect)


def _free_shirt(club) -> int:
    """El dorsal libre mas bajo (1..99)."""
    used = {p.shirt_number for p in club.players if p.shirt_number}
    return next(n for n in range(1, 100) if n not in used)
