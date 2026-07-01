"""Economia base: valor y sueldo de un jugador.

Primer balanceo, deliberadamente a **escala chica estilo Hattrick** (presupuesto
inicial ~200k, sueldos ~400 a ~1200). Son funciones PURAS y deterministas
(dependen solo del jugador y, opcionalmente, de la fecha del juego para la edad).
Se van a afinar cuando existan ingresos (entradas, patrocinadores) y el ciclo
semanal. NO importan Textual (viven en simulation/).
"""

from datetime import date

from .. import config
from ..domain.player import Player

# Presupuesto inicial del club del jugador (numeros chicos, como Hattrick).
STARTING_BUDGET = 200_000

# --- Sueldo semanal ---
_SALARY_BASE = 150      # piso base antes de sumar por habilidad
_SALARY_PER_OVR = 13    # cuanto suma cada punto de overall
_SALARY_MIN = 400       # sueldo minimo (nadie cobra menos)

# --- Valor de mercado ---
_VALUE_K = 6            # escala general del valor


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
    """Sueldo semanal del jugador (dominado por el overall, ajustado por edad)."""
    today = today or config.SEASON_START_DATE
    base = _SALARY_BASE + player.overall * _SALARY_PER_OVR
    return max(_SALARY_MIN, round(base * _age_salary_factor(player.age_on(today))))


def player_value(player: Player, today: date | None = None) -> int:
    """Valor de mercado: crece con overall y potencial, decae con la edad."""
    today = today or config.SEASON_START_DATE
    skill = player.overall * player.overall
    # El potencial sin explotar suma valor (proyeccion de mejora).
    upside = 1.0 + max(0.0, player.potential - player.overall) / 100 * 2
    value = skill * _VALUE_K * upside * _age_value_factor(player.age_on(today))
    return round(value)


def squad_wage_bill(players: list[Player], today: date | None = None) -> int:
    """Masa salarial semanal: suma de los sueldos del plantel."""
    return sum(player_salary(p, today) for p in players)
