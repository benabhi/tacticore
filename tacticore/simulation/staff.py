"""Cuerpo de trabajo del club: sueldos, cupos, contratacion y efectos.

Los empleados (`domain/employee.py`) son un framework aparte del DT. Cada rol
engancha con un sistema vivo del juego:
- MEDICO -> baja la probabilidad de lesion y acorta las bajas (ver discipline.py).
- DIRECTOR FINANCIERO -> mejora los ingresos semanales (ver daily._weekly_economy).

Todo es logica pura (sin Textual). El sueldo (`staff_wage`) es la BARRERA: escala
convexo con el skill y por nivel de liga, asi un empleado mejor pesa mucho mas en la
caja. Se pueden tener VARIOS empleados por rol, con un tope por tier (`_TIER_SLOTS`);
cuando se apilan, su efecto tiene rendimiento decreciente (no suma lineal).
"""

from ..domain.club import Club
from ..domain.employee import Employee
from ..domain.enums import EmployeeRole, LeagueTier

# --- Sueldo semanal (barrera; convexo en skill, escalado por tier) ---
# Base ~ el sueldo de un empleado de skill 50 en la liga E; crece fuerte hacia arriba.
_ROLE_BASE: dict[EmployeeRole, int] = {
    EmployeeRole.DOCTOR: 600,
    EmployeeRole.FINANCE: 600,
}
_TIER_WAGE_MULT: dict[LeagueTier, float] = {
    LeagueTier.A: 6.0,
    LeagueTier.B: 4.0,
    LeagueTier.C: 2.5,
    LeagueTier.D: 1.5,
    LeagueTier.E: 1.0,
}
_WAGE_MIN = 300  # piso: ningun empleado cobra menos

# --- Cupos por rol segun el nivel de liga (varios por rol en tiers altos) ---
_TIER_SLOTS: dict[LeagueTier, int] = {
    LeagueTier.A: 3,
    LeagueTier.B: 2,
    LeagueTier.C: 2,
    LeagueTier.D: 1,
    LeagueTier.E: 1,
}

# --- Magnitud de los efectos (tuneables) ---
_DOC_PREVENT = 0.5   # un medico de 100 reduce ~50% la probabilidad de lesion
_DOC_HEAL = 0.35     # y acorta ~35% las semanas de baja (del mejor medico)
_FIN_RATE = 0.12     # un director de 100 suma ~12% de ingresos...
_FIN_CAP = 0.15      # ...con tope 15% aun apilando varios


def staff_wage(role: EmployeeRole, skill: float, tier: LeagueTier) -> int:
    """Sueldo semanal de un empleado (convexo en skill, escalado por tier)."""
    base = _ROLE_BASE[role]
    return max(_WAGE_MIN, round(base * (0.5 + skill / 100) ** 2 * _TIER_WAGE_MULT[tier]))


def staff_slots(role: EmployeeRole, tier: LeagueTier) -> int:
    """Cuantos empleados de `role` puede tener un club de la liga `tier`."""
    return _TIER_SLOTS[tier]


def employees_of(club: Club, role: EmployeeRole) -> list[Employee]:
    """Empleados del club con ese rol."""
    return [e for e in club.employees if e.role is role]


def role_count(club: Club, role: EmployeeRole) -> int:
    """Cuantos empleados de `role` tiene contratados el club."""
    return len(employees_of(club, role))


def can_hire(club: Club, role: EmployeeRole) -> bool:
    """True si al club le queda cupo libre para contratar otro empleado de `role`."""
    return role_count(club, role) < staff_slots(role, club.tier)


def hire(game, employee: Employee) -> bool:
    """Contrata a `employee` en el club del jugador si hay cupo. Devuelve si pudo.

    No cobra prima de fichaje: la barrera es el sueldo semanal (se descuenta en el
    cierre economico de los viernes)."""
    club = game.player_club
    if club is None or not can_hire(club, employee.role):
        return False
    club.employees.append(employee)
    return True


def fire(game, employee: Employee) -> None:
    """Despide a `employee` del club del jugador (libera cupo; sin indemnizacion)."""
    club = game.player_club
    if club is not None and employee in club.employees:
        club.employees.remove(employee)


def staff_wage_bill(club: Club) -> int:
    """Masa salarial semanal del cuerpo de trabajo."""
    return sum(e.weekly_wage for e in club.employees)


# --- Agregadores de efecto (rendimiento decreciente al apilar) ---
def injury_factor(club: Club) -> float:
    """Factor multiplicativo (0,1] sobre la probabilidad de lesion.

    Cada medico multiplica por `(1 - _DOC_PREVENT*skill/100)`; al apilar, el efecto
    se compone (decreciente y acotado, nunca baja de 0)."""
    factor = 1.0
    for doc in employees_of(club, EmployeeRole.DOCTOR):
        factor *= 1 - _DOC_PREVENT * doc.skill / 100
    return factor


def injury_weeks_factor(club: Club) -> float:
    """Factor (0,1] sobre las semanas de baja de una lesion nueva.

    Lo aporta el MEJOR medico (no se apila la recuperacion)."""
    docs = employees_of(club, EmployeeRole.DOCTOR)
    if not docs:
        return 1.0
    best = max(d.skill for d in docs)
    return 1 - _DOC_HEAL * best / 100


def role_effect_desc(role: EmployeeRole, skill: float) -> str:
    """Texto corto del aporte de UN empleado de ese rol y habilidad (para la UI)."""
    if role is EmployeeRole.DOCTOR:
        return (f"-{round(_DOC_PREVENT * skill)}% riesgo de lesion, "
                f"-{round(_DOC_HEAL * skill)}% tiempo de baja")
    if role is EmployeeRole.FINANCE:
        return f"+{round(_FIN_RATE * skill)}% ingresos (cuota + instalaciones)"
    return ""


def finance_income_bonus(club: Club) -> float:
    """Fraccion extra de ingreso semanal por la direccion financiera.

    El mejor director aporta `_FIN_RATE*skill/100`; los siguientes, la mitad; todo
    acotado a `_FIN_CAP`."""
    dirs = sorted(
        (e.skill for e in employees_of(club, EmployeeRole.FINANCE)), reverse=True
    )
    bonus = 0.0
    for i, skill in enumerate(dirs):
        weight = 1.0 if i == 0 else 0.5
        bonus += _FIN_RATE * skill / 100 * weight
    return min(_FIN_CAP, bonus)
