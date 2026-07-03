"""Economia del club: sueldos, valor de mercado, taquilla e ingresos base.

Escala chica estilo Hattrick (presupuesto inicial ~200k; sueldos de ~$250 en la
liga E a decenas de miles en la A). Funciones PURAS y deterministas (dependen solo
de las entidades y, para la edad, de la fecha del juego). Los numeros crecen solos
por division porque dependen del overall (que ya escala por tier). NO importan
Textual (viven en simulation/).
"""

from datetime import date

from .. import config
from ..domain.club import Club
from ..domain.player import Player

# Presupuesto inicial del club del jugador (numeros chicos, como Hattrick).
STARTING_BUDGET = 200_000

# --- Precio de entrada por sector del estadio (fijo, estilo Hattrick) ---
TICKET_PRICES: dict[str, int] = {
    "general": 45, "preferente": 75, "tribuna": 90, "palco": 300,
}
# Orden de llenado: del sector mas barato al mas caro (los baratos se ocupan antes).
_FILL_ORDER = ("general", "preferente", "tribuna", "palco")

# --- Sueldo semanal (potencia convexa del overall) ---
# Calibrado a: OVR35~=$400, OVR55~=$3000 (techo de E), OVR78~=$15k, OVR90~=$28k.
_SALARY_K = 4.5e-5
_SALARY_EXP = 4.5
_SALARY_MIN = 300        # piso: nadie cobra menos (extremo bajo del rango de E)
_SPECIALTY_MULT = 1.15   # una especialidad encarece al jugador

# --- Valor de mercado ---
_VALUE_K = 6

# --- Asistencia y economia semanal (primer tanteo, escala chica) ---
_ATTEND_RATE = 0.55     # fraccion de socios que va a un partido tipico de local
_MEMBER_DUES = 5        # ingreso semanal por socio (cuota)
_STADIUM_UPKEEP = 0.15  # gasto semanal de mantenimiento por butaca


def _age_salary_factor(age: int) -> float:
    """Los jugadores en su pico cobran un poco mas; jovenes y veteranos, menos."""
    if age <= 20:
        return 0.90
    if age <= 30:
        return 1.00
    if age <= 33:
        return 0.95
    return 0.85


def _age_value_factor(age: int) -> float:
    """El valor de reventa cae con la edad (un pibe vale mas que un veterano)."""
    if age <= 18:
        return 1.30
    if age <= 23:
        return 1.20
    if age <= 27:
        return 1.00
    if age <= 30:
        return 0.75
    if age <= 33:
        return 0.50
    return 0.30


def player_salary(player: Player, today: date | None = None) -> int:
    """Sueldo semanal: potencia del overall, ajustado por edad, forma y especialidad."""
    today = today or config.SEASON_START_DATE
    base = _SALARY_K * (player.overall ** _SALARY_EXP)
    mult = _age_salary_factor(player.age_on(today))
    mult *= _SPECIALTY_MULT if player.specialty else 1.0
    mult *= 0.9 + 0.2 * (player.form / 100)   # la buena forma encarece un poco
    return max(_SALARY_MIN, round(base * mult))


def player_value(player: Player, today: date | None = None) -> int:
    """Valor de mercado: crece con overall y potencial, decae con la edad."""
    today = today or config.SEASON_START_DATE
    skill = player.overall * player.overall
    upside = 1.0 + max(0.0, player.potential - player.overall) / 100 * 2
    value = skill * _VALUE_K * upside * _age_value_factor(player.age_on(today))
    return round(value)


def squad_wage_bill(players: list[Player], today: date | None = None) -> int:
    """Masa salarial semanal: suma de los sueldos del plantel."""
    return sum(player_salary(p, today) for p in players)


def membership_income(members: int) -> int:
    """Ingreso semanal por la cuota de los socios."""
    return round(members * _MEMBER_DUES)


def stadium_upkeep(capacity: int) -> int:
    """Gasto semanal de mantenimiento del estadio (segun su capacidad)."""
    return round(capacity * _STADIUM_UPKEEP)


def _rival_factor(home: Club, away: Club) -> float:
    """Un rival mas grande convoca mas gente (dentro de un rango acotado)."""
    strength = away.overall / (home.overall + away.overall + 1)  # 0..1
    return max(0.85, min(1.30, 0.85 + strength))


def expected_attendance(home: Club, away: Club) -> int:
    """Cuanta gente se espera para un partido de local (tope: la capacidad).

    La popularidad de las instalaciones del local multiplica la demanda.
    """
    from .facilities import facility_popularity

    demand = home.members * _ATTEND_RATE * _rival_factor(home, away)
    demand *= 1 + facility_popularity(home)
    return int(min(home.stadium.capacity, round(demand)))


def matchday_income(home: Club, away: Club) -> int:
    """Recaudacion de taquilla de un partido de local.

    Se llenan los sectores del mas barato al mas caro hasta cubrir la asistencia
    esperada; el ingreso es la suma de asientos ocupados por su precio.
    """
    remaining = expected_attendance(home, away)
    income = 0
    for sector in _FILL_ORDER:
        seats = getattr(home.stadium, sector)
        taken = min(remaining, seats)
        income += taken * TICKET_PRICES[sector]
        remaining -= taken
        if remaining <= 0:
            break
    return income
