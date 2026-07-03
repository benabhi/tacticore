"""Entidades de instalaciones: la especificacion del catalogo y la obra en curso.

`FacilitySpec` es el dato ESTATICO de un edificio del catalogo (costo, tier, efecto,
etc.); el catalogo concreto y toda la logica (construir, mejorar, ingresos) viven en
`simulation/facilities.py`. `Construction` es el estado MUTABLE de una obra que el
club tiene en marcha (baja un dia por vez en el loop diario hasta completarse).
"""

from dataclasses import dataclass

from .enums import LeagueTier


@dataclass(frozen=True)
class FacilitySpec:
    """Especificacion de un edificio del catalogo (dato estatico)."""

    id: str
    name: str
    category: str                       # "Comercial", "Deportivo", ...
    min_tier: LeagueTier                # tier minimo para poder construirlo
    requires: tuple[tuple[str, int], ...]  # (id_edificio, nivel_minimo) necesarios
    plots: int                          # parcelas que ocupa
    max_level: int
    base_cost: int                      # costo del nivel 1 (crece por nivel)
    build_days: int                     # dias de obra por nivel
    weekly_income: int                  # ingreso/semana del nivel 1 (crece por nivel)
    popularity: float                   # bonus de popularidad del nivel 1
    buildable: bool = True              # False = referencia "proximamente" (no se puede)
    future_note: str = ""               # que hara cuando se implemente (si no es buildable)


@dataclass
class Construction:
    """Una obra en curso del club (edificio o grada)."""

    kind: str            # "facility" | "stand"
    key: str             # id del edificio, o nombre del sector de la grada
    days_remaining: int
