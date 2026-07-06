"""Instalaciones: catalogo de edificios, gradas del estadio, parcelas y logica.

Funciones PURAS sobre el club (sin UI): construir/mejorar, comprar parcelas, avanzar
las obras (que corren en el loop diario) y calcular sus efectos economicos (ingreso
semanal y popularidad, que sube la asistencia). El catalogo es data-driven
(`CATALOG`); el estado del club vive en `club.facilities` (id -> nivel),
`club.stands_built`, `club.plots` y `club.constructions`.
"""

from ..domain.club import Club
from ..domain.enums import LeagueTier
from ..domain.facility import Construction, FacilitySpec

# Ranking de tier (A el mejor). Un club puede construir algo de `min_tier` si su
# tier es AL MENOS tan bueno (rank >=). Ej: min_tier=C -> lo pueden A, B y C.
_TIER_RANK: dict[LeagueTier, int] = {
    LeagueTier.E: 1, LeagueTier.D: 2, LeagueTier.C: 3, LeagueTier.B: 4, LeagueTier.A: 5,
}

# Costo y efecto crecen por nivel. Costo del nivel N = base * _COST_GROWTH**(N-1);
# ingreso/popularidad del nivel N = base * N (lineal).
_COST_GROWTH = 1.8

# Catalogo de edificios. Los "Deportivo" con buildable=False son referencias del
# roadmap (se ven "proximamente"): su efecto llega en su milestone.
CATALOG: tuple[FacilitySpec, ...] = (
    FacilitySpec("shop", "Tienda oficial", "Comercial", LeagueTier.E, (), 1, 3,
                 8_000, 4, 300, 0.03),
    FacilitySpec("food", "Zona de comida", "Comercial", LeagueTier.E, (), 1, 3,
                 6_000, 4, 400, 0.0),
    FacilitySpec("parking", "Estacionamiento", "Comercial", LeagueTier.D, (), 1, 3,
                 12_000, 5, 250, 0.0),
    FacilitySpec("museum", "Museo del club", "Comercial", LeagueTier.D, (("shop", 1),),
                 1, 3, 20_000, 6, 600, 0.05),
    FacilitySpec("screens", "Pantallas e iluminacion", "Comercial", LeagueTier.C, (),
                 1, 3, 25_000, 6, 0, 0.10),
    FacilitySpec("mall", "Centro comercial", "Comercial", LeagueTier.B,
                 (("parking", 1),), 2, 3, 120_000, 9, 3_000, 0.0),
    FacilitySpec("hotel", "Hotel del club", "Comercial", LeagueTier.A, (("mall", 1),),
                 2, 3, 400_000, 12, 8_000, 0.08),
    # --- Deportivo / Gestion (efecto especial, no ingreso: ver funciones abajo) ---
    FacilitySpec("training", "Centro de entrenamiento", "Deportivo", LeagueTier.E, (),
                 1, 3, 10_000, 5, 0, 0.0),
    FacilitySpec("medical", "Enfermeria", "Deportivo", LeagueTier.D, (), 1, 3,
                 15_000, 6, 0, 0.0),
    FacilitySpec("oficina", "Oficinas administrativas", "Gestion", LeagueTier.D, (),
                 1, 3, 12_000, 5, 0, 0.0),
    # --- Referencias (proximamente) ---
    FacilitySpec("youth", "Complejo juvenil", "Deportivo", LeagueTier.C, (), 1, 3,
                 0, 0, 0, 0.0, buildable=False,
                 future_note="Alimentara la cantera con juveniles."),
)
_BY_ID: dict[str, FacilitySpec] = {s.id: s for s in CATALOG}

# Gradas del estadio: sector -> (asientos que suma, costo, dias, tier minimo).
# Cada grada ocupa 1 parcela.
STANDS: dict[str, tuple[int, int, int, LeagueTier]] = {
    "general": (2000, 30_000, 6, LeagueTier.E),
    "preferente": (1000, 25_000, 6, LeagueTier.E),
    "tribuna": (500, 18_000, 5, LeagueTier.E),
    "palco": (200, 40_000, 7, LeagueTier.C),
}
_STAND_LABEL = {"general": "Grada general", "preferente": "Grada preferente",
                "tribuna": "Grada tribuna", "palco": "Palcos"}

# Parcelas: se arranca SIN parcelas (hay que comprarlas). El costo depende del tier y
# crece con cada parcela comprada (`plot_cost`).
START_PLOTS = 0
_PLOT_BASE: dict[LeagueTier, int] = {
    LeagueTier.E: 15_000, LeagueTier.D: 30_000, LeagueTier.C: 60_000,
    LeagueTier.B: 120_000, LeagueTier.A: 250_000,
}


# --- Consultas de catalogo ---
def spec(facility_id: str) -> FacilitySpec:
    return _BY_ID[facility_id]


def level(club: Club, facility_id: str) -> int:
    return club.facilities.get(facility_id, 0)


def build_cost(s: FacilitySpec, target_level: int) -> int:
    """Costo de construir/mejorar hasta `target_level` (1 = construir)."""
    return round(s.base_cost * _COST_GROWTH ** (target_level - 1))


def stand_label(sector: str) -> str:
    return _STAND_LABEL[sector]


def _tier_ok(club: Club, min_tier: LeagueTier) -> bool:
    return _TIER_RANK[club.tier] >= _TIER_RANK[min_tier]


def _in_progress(club: Club, kind: str, key: str) -> bool:
    return any(c.kind == kind and c.key == key for c in club.constructions)


def facility_status(club: Club, facility_id: str) -> str:
    """Estado para la UI: coming_soon/maxed/in_progress/locked_tier/locked_req/
    upgradable/buildable."""
    s = _BY_ID[facility_id]
    if not s.buildable:
        return "coming_soon"
    lv = level(club, facility_id)
    if _in_progress(club, "facility", facility_id):
        return "in_progress"
    if lv >= s.max_level:
        return "maxed"
    if not _tier_ok(club, s.min_tier):
        return "locked_tier"
    if any(level(club, rid) < rlv for rid, rlv in s.requires):
        return "locked_req"
    return "upgradable" if lv >= 1 else "buildable"


# --- Parcelas ---
def plot_cost(club: Club) -> int:
    base = _PLOT_BASE[club.tier]
    extra = max(0, club.plots - START_PLOTS)
    return round(base * 1.2 ** extra)


def plots_used(club: Club) -> int:
    """Parcelas ocupadas: edificios construidos + gradas + obras que reservan una."""
    used = sum(_BY_ID[fid].plots for fid, lv in club.facilities.items() if lv > 0)
    used += club.stands_built
    for c in club.constructions:
        if c.kind == "stand":
            used += 1
        elif c.kind == "facility" and level(club, c.key) == 0:
            used += _BY_ID[c.key].plots  # primer construccion: reserva su parcela
    return used


def plots_free(club: Club) -> int:
    return club.plots - plots_used(club)


def buy_plot(club: Club) -> bool:
    """Compra una parcela si hay plata. Devuelve si se concreto."""
    cost = plot_cost(club)
    if club.capital < cost:
        return False
    club.capital -= cost
    club.plots += 1
    return True


# --- Construir / mejorar ---
def start_facility(club: Club, facility_id: str) -> bool:
    """Inicia la obra de un edificio (construir o mejorar) si se puede pagar/ubicar."""
    s = _BY_ID[facility_id]
    if facility_status(club, facility_id) not in ("buildable", "upgradable"):
        return False
    target = level(club, facility_id) + 1
    cost = build_cost(s, target)
    needs_plot = level(club, facility_id) == 0
    if club.capital < cost or (needs_plot and plots_free(club) < s.plots):
        return False
    club.capital -= cost
    club.constructions.append(Construction("facility", facility_id, s.build_days))
    return True


def stand_status(club: Club, sector: str) -> str:
    """Estado de una grada para la UI: in_progress / locked_tier / buildable."""
    if _in_progress(club, "stand", sector):
        return "in_progress"
    if not _tier_ok(club, STANDS[sector][3]):
        return "locked_tier"
    return "buildable"


def can_build_stand(club: Club, sector: str) -> bool:
    _, _, _, min_tier = STANDS[sector]
    return _tier_ok(club, min_tier) and not _in_progress(club, "stand", sector)


def start_stand(club: Club, sector: str) -> bool:
    """Inicia la obra de una grada (suma asientos al completarse)."""
    seats, cost, days, min_tier = STANDS[sector]
    if not can_build_stand(club, sector):
        return False
    if club.capital < cost or plots_free(club) < 1:
        return False
    club.capital -= cost
    club.constructions.append(Construction("stand", sector, days))
    return True


def tick_constructions(club: Club) -> list[Construction]:
    """Avanza un dia las obras del club; completa y aplica las que llegan a 0."""
    if not club.constructions:
        return []
    done: list[Construction] = []
    for c in club.constructions:
        c.days_remaining -= 1
        if c.days_remaining <= 0:
            done.append(c)
    for c in done:
        club.constructions.remove(c)
        if c.kind == "facility":
            club.facilities[c.key] = club.facilities.get(c.key, 0) + 1
        else:  # stand
            seats = STANDS[c.key][0]
            setattr(club.stadium, c.key, getattr(club.stadium, c.key) + seats)
            club.stands_built += 1
    return done


# --- Efectos economicos ---
def facility_income(club: Club) -> int:
    """Ingreso semanal total de las instalaciones construidas."""
    return sum(_BY_ID[fid].weekly_income * lv for fid, lv in club.facilities.items() if lv > 0)


def facility_popularity(club: Club) -> float:
    """Bonus de popularidad total (multiplica la asistencia)."""
    return sum(_BY_ID[fid].popularity * lv for fid, lv in club.facilities.items() if lv > 0)


# --- Efectos especiales de instalaciones deportivas/gestion (por id + nivel) ---
# Estas instalaciones no dan ingreso directo: su efecto se computa aca y lo consumen
# staff.py (lesiones/cupos/ingresos) y formation_training (entrenamiento).
_MEDICAL_PREVENT_PER_LVL = 0.06   # -6% probabilidad de lesion por nivel (multiplicativo)
_MEDICAL_RECOVER_PER_LVL = 0.08   # -8% tiempo de baja por nivel
_TRAINING_BOOST_PER_LVL = 0.15    # +15% ganancia de entrenamiento por nivel
_OFFICE_INCOME_PER_LVL = 0.03     # +3% ingreso semanal por nivel


def medical_injury_factor(club: Club) -> float:
    """Factor (0,1] sobre la probabilidad de lesion por la Enfermeria."""
    return 1 - _MEDICAL_PREVENT_PER_LVL * level(club, "medical")


def medical_recover_factor(club: Club) -> float:
    """Factor (0,1] sobre el tiempo de baja por la Enfermeria."""
    return 1 - _MEDICAL_RECOVER_PER_LVL * level(club, "medical")


def training_boost(club: Club) -> float:
    """Multiplicador de la ganancia de entrenamiento por el Centro de entrenamiento."""
    return 1 + _TRAINING_BOOST_PER_LVL * level(club, "training")


def office_income_bonus(club: Club) -> float:
    """Fraccion extra de ingreso semanal por las Oficinas administrativas."""
    return _OFFICE_INCOME_PER_LVL * level(club, "oficina")


def facility_effect_desc(facility_id: str) -> str:
    """Texto del efecto POR NIVEL de una instalacion deportiva/gestion (o '' si no tiene)."""
    return {
        "medical": "+1 cupo Medico y -6% lesiones por nivel",
        "training": "+15% entrenamiento por nivel",
        "oficina": "+1 cupo Dir. financiero y +3% ingresos por nivel",
    }.get(facility_id, "")
