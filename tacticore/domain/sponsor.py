"""Entidades de patrocinio: la marca (Sponsor) y el contrato firmado.

Un club tiene un patrocinador principal, con el que firma un CONTRATO: una
duracion en semanas, un pago semanal fijo y posibles bonus (por ascender de
categoria y por hilar una racha de victorias). El generador ofrece varias marcas
con terminos distintos (ver generators/sponsor_generator.py); el jugador elige una
al fundar el club y podra renovar/cambiar cuando el contrato se agote.
"""

from dataclasses import dataclass


@dataclass
class Sponsor:
    """La marca patrocinadora (identidad)."""

    name: str
    sector: str   # rubro de la marca (ej. "Bebidas", "Banca"), solo sabor
    tier: int     # calidad de la marca (1 = modesta, 5 = grande)


@dataclass
class SponsorContract:
    """El acuerdo firmado con un patrocinador, para un club."""

    sponsor: Sponsor
    weeks_total: int       # duracion total del contrato (semanas)
    weeks_remaining: int   # semanas que faltan (baja cada viernes economico)
    weekly_pay: int        # ingreso fijo por semana
    signing_bonus: int = 0     # pago unico al firmar
    promotion_bonus: int = 0   # se cobra si el club asciende de categoria
    streak_bonus: int = 0      # se cobra al hilar `streak_len` victorias
    streak_len: int = 0        # cuantas victorias seguidas gatillan el bonus

    @property
    def active(self) -> bool:
        """True mientras al contrato le queden semanas."""
        return self.weeks_remaining > 0
