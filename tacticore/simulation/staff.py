"""Cuerpo de trabajo del club: bonus, sueldos, cupos, contratacion y efectos.

Cada empleado (`domain/employee.py`) tiene un ROL (titulo + cupo) y 1-3 BONUS (tipo ->
fuerza 1-100): el primario del rol mas 0-2 extra de la BOLSA de su rol. Los efectos se
agregan POR TIPO sobre todos los empleados; el sueldo escala con el PODER total (suma de
fuerzas), convexo y por tier, como barrera economica. Los bonus de entrenamiento/moral
existen pero todavia son INERTES (sin sistema que los consuma).

Logica pura (sin Textual).
"""

from ..domain.club import Club
from ..domain.employee import Employee
from ..domain.enums import BonusType, EmployeeRole, LeagueTier
from . import facilities as fac

B = BonusType

# --- Roles: bonus primario y BOLSA de extras (ligada al rol) ---
_ROLE_PRIMARY: dict[EmployeeRole, BonusType] = {
    EmployeeRole.DOCTOR: B.INJURY_PREVENT,
    EmployeeRole.FINANCE: B.INCOME,
    EmployeeRole.ASSISTANT: B.TRAINING,
    EmployeeRole.PSYCHOLOGIST: B.MORALE,
}
_ROLE_EXTRAS: dict[EmployeeRole, list[BonusType]] = {
    EmployeeRole.DOCTOR: [B.INJURY_RECOVER, B.TRAINING, B.MORALE],   # salud/bienestar
    EmployeeRole.FINANCE: [B.GATE, B.TRANSFERS, B.WAGES],            # dinero
    EmployeeRole.ASSISTANT: [B.MORALE, B.INJURY_RECOVER],            # cuerpo tecnico
    EmployeeRole.PSYCHOLOGIST: [B.TRAINING, B.INJURY_PREVENT],       # cabeza/bienestar
}

# --- Magnitud y modo de agregacion de cada tipo de bonus ---
# rate = cuanto aporta una fuerza 100; cap = tope al apilar (para los aditivos).
_RATE: dict[BonusType, float] = {
    B.INJURY_PREVENT: 0.50, B.INJURY_RECOVER: 0.35, B.INCOME: 0.12,
    B.GATE: 0.10, B.TRANSFERS: 0.15, B.WAGES: 0.08, B.TRAINING: 0.0, B.MORALE: 0.0,
}
_CAP: dict[BonusType, float] = {
    B.INCOME: 0.15, B.GATE: 0.12, B.TRANSFERS: 0.20, B.WAGES: 0.10,
}
# Tipos con efecto real hoy (los demas se muestran marcados "proximo").
_LIVE = {B.INJURY_PREVENT, B.INJURY_RECOVER, B.INCOME, B.GATE, B.TRANSFERS, B.WAGES,
         B.TRAINING, B.MORALE}
# El bonus de entrenamiento aporta PUNTOS a la capacidad de entreno (no un %).
_TRAIN_PTS_RATE = 0.20   # una fuerza 100 -> ~20 puntos de capacidad
_TRAIN_PTS_CAP = 25
# La moral aporta PUNTOS al liderazgo efectivo (no un %): sube la moral base del
# plantel junto al DT (ver daily._drift_morale). Una fuerza 100 -> ~25 puntos.
_MORALE_PTS_RATE = 0.25
_MORALE_PTS_CAP = 30

# --- Sueldo (barrera; convexo en el poder total, escalado por tier) ---
_WAGE_BASE = 600   # sueldo de un empleado de poder 50 en la liga E
_TIER_WAGE_MULT: dict[LeagueTier, float] = {
    LeagueTier.A: 6.0, LeagueTier.B: 4.0, LeagueTier.C: 2.5,
    LeagueTier.D: 1.5, LeagueTier.E: 1.0,
}
_WAGE_MIN = 300

# --- Cupos por rol: base por tier + nivel de la instalacion "hogar" del rol ---
# El base sube al ascender de liga; construir/mejorar la instalacion ancla suma mas.
_TIER_SLOT_BASE: dict[LeagueTier, int] = {
    LeagueTier.E: 1, LeagueTier.D: 1, LeagueTier.C: 1, LeagueTier.B: 2, LeagueTier.A: 2,
}
_HOME_FACILITY: dict[EmployeeRole, str] = {
    EmployeeRole.DOCTOR: "medical",       # Enfermeria
    EmployeeRole.FINANCE: "oficina",      # Oficinas administrativas
    EmployeeRole.ASSISTANT: "training",   # Centro de entrenamiento
    EmployeeRole.PSYCHOLOGIST: "medical",  # Enfermeria (salud fisica y mental)
}
_INCOME_COMBINED_CAP = 0.20  # tope del bonus de ingresos (empleados + oficina)


def role_primary(role: EmployeeRole) -> BonusType:
    return _ROLE_PRIMARY[role]


def role_extras(role: EmployeeRole) -> list[BonusType]:
    return _ROLE_EXTRAS[role]


def is_live(t: BonusType) -> bool:
    """True si el tipo de bonus tiene efecto real hoy."""
    return t in _LIVE


def staff_wage(power: float, tier: LeagueTier) -> int:
    """Sueldo semanal por poder total (convexo), escalado por tier."""
    return max(_WAGE_MIN, round(_WAGE_BASE * (0.5 + power / 100) ** 2 * _TIER_WAGE_MULT[tier]))


def coach_wage(coach, tier: LeagueTier) -> int:
    """Sueldo semanal del DT, calculado al vuelo (no se persiste, como el del jugador).

    El DT es el staff mas caro: su "poder" combina habilidad y liderazgo."""
    if coach is None:
        return 0
    power = coach.skill + 0.5 * coach.leadership
    return staff_wage(power, tier)


def bonus_desc(t: BonusType, strength: float) -> str:
    """Texto corto del efecto de UN bonus (para la UI). Inerte -> '(proximo)'."""
    if t is B.TRAINING:
        return f"+{round(_TRAIN_PTS_RATE * strength)} de entrenamiento"
    if t is B.MORALE:
        return f"+{round(_MORALE_PTS_RATE * strength)} a la moral"
    pct = round(_RATE[t] * strength)
    text = {
        B.INJURY_PREVENT: f"-{pct}% lesiones",
        B.INJURY_RECOVER: f"-{pct}% tiempo de baja",
        B.INCOME: f"+{pct}% ingresos",
        B.GATE: f"+{pct}% taquilla",
        B.TRANSFERS: f"+{pct}% en ventas",
        B.WAGES: f"-{pct}% sueldos",
    }.get(t)
    if text is None:  # inerte (moral)
        return f"{t.value} (proximo)"
    return text


def training_bonus(club: Club) -> float:
    """Puntos de capacidad de entrenamiento que aportan los empleados (bonus TRAINING)."""
    total = 0.0
    for i, s in enumerate(_strengths(club, B.TRAINING)):
        total += _TRAIN_PTS_RATE * s * (1.0 if i == 0 else 0.5)
    return min(_TRAIN_PTS_CAP, total)


def morale_support(club: Club) -> float:
    """Puntos de liderazgo efectivo que aporta el staff (bonus MORALE, ej. Psicologo).

    Se suman al liderazgo del DT para fijar la moral base del plantel (ver
    daily._drift_morale). Rendimiento decreciente y tope, como el entrenamiento."""
    total = 0.0
    for i, s in enumerate(_strengths(club, B.MORALE)):
        total += _MORALE_PTS_RATE * s * (1.0 if i == 0 else 0.5)
    return min(_MORALE_PTS_CAP, total)


# --- Cupos, contratacion, sueldos ---
def staff_slots(club: Club, role: EmployeeRole) -> int:
    """Cupos de `role`: base por tier + nivel de la instalacion hogar del rol.

    El base crece al ascender de liga y el edificio ancla (Enfermeria/Centro de
    entrenamiento/Oficinas) suma su nivel encima."""
    return _TIER_SLOT_BASE[club.tier] + fac.level(club, _HOME_FACILITY[role])


def employees_of(club: Club, role: EmployeeRole) -> list[Employee]:
    return [e for e in club.employees if e.role is role]


def role_count(club: Club, role: EmployeeRole) -> int:
    return len(employees_of(club, role))


def can_hire(club: Club, role: EmployeeRole) -> bool:
    return role_count(club, role) < staff_slots(club, role)


def hire(game, employee: Employee) -> bool:
    """Contrata a `employee` en el club del jugador si hay cupo (sin prima; la barrera
    es el sueldo semanal)."""
    club = game.player_club
    if club is None or not can_hire(club, employee.role):
        return False
    club.employees.append(employee)
    return True


def fire(game, employee: Employee) -> None:
    club = game.player_club
    if club is not None and employee in club.employees:
        club.employees.remove(employee)


def replace_coach(game, coach) -> None:
    """Reemplaza al DT del club del jugador (siempre hay uno: no se despide, se cambia)."""
    club = game.player_club
    if club is not None:
        club.coach = coach


def staff_wage_bill(club: Club) -> int:
    """Masa salarial del cuerpo de trabajo: empleados + el DT (sueldo calculado)."""
    return sum(e.weekly_wage for e in club.employees) + coach_wage(club.coach, club.tier)


# --- Agregacion de efectos POR TIPO (sobre todos los empleados) ---
def _strengths(club: Club, t: BonusType) -> list[float]:
    """Fuerzas del bonus `t` en el plantel de empleados, de mayor a menor."""
    return sorted((e.bonuses[t] for e in club.employees if t in e.bonuses), reverse=True)


def _reduce_mult(club: Club, t: BonusType) -> float:
    """Reduccion multiplicativa (0,1]: cada empleado compone su factor (para lesiones)."""
    factor = 1.0
    for s in _strengths(club, t):
        factor *= 1 - _RATE[t] * s / 100
    return factor


def _reduce_best(club: Club, t: BonusType) -> float:
    """Reduccion del MEJOR empleado (no se apila): factor (0,1]."""
    ss = _strengths(club, t)
    return 1 - _RATE[t] * ss[0] / 100 if ss else 1.0


def _add(club: Club, t: BonusType) -> float:
    """Bonus aditivo con rendimiento decreciente y tope (para ingresos/taquilla/...)."""
    total = 0.0
    for i, s in enumerate(_strengths(club, t)):
        total += _RATE[t] * s / 100 * (1.0 if i == 0 else 0.5)
    return min(_CAP[t], total)


# API que consumen los sistemas del juego (combinan empleados + instalaciones).
def injury_factor(club: Club) -> float:
    """Prob. de lesion: empleados (prevencion) x la Enfermeria."""
    return _reduce_mult(club, B.INJURY_PREVENT) * fac.medical_injury_factor(club)


def injury_weeks_factor(club: Club) -> float:
    """Tiempo de baja: mejor medico x la Enfermeria."""
    return _reduce_best(club, B.INJURY_RECOVER) * fac.medical_recover_factor(club)


def income_bonus(club: Club) -> float:
    """Ingresos extra: empleados (income) + las Oficinas, con tope combinado."""
    return min(_INCOME_COMBINED_CAP, _add(club, B.INCOME) + fac.office_income_bonus(club))


def gate_bonus(club: Club) -> float:
    return _add(club, B.GATE)


def transfer_bonus(club: Club) -> float:
    return _add(club, B.TRANSFERS)


def wage_reduction(club: Club) -> float:
    return _add(club, B.WAGES)
