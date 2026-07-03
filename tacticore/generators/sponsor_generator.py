"""Generador de patrocinadores y sus ofertas de contrato (deterministas).

Cada marca es de fantasia (raiz + sufijo, ver data/sponsor_data.py). Las OFERTAS
que recibe un club dependen de su nivel de liga (mejor liga -> mas plata) y vienen
en tres variantes para que la eleccion importe: corta y bien paga (sin bonus),
media (con bonus por ascenso) y larga (pago menor + bonus por racha y ascenso).
"""

import random

from ..domain.enums import LeagueTier
from ..domain.sponsor import Sponsor, SponsorContract
from .data import sponsor_data

# Pago semanal base por nivel de liga (los numeros crecen mucho hacia arriba).
_TIER_BASE_PAY: dict[LeagueTier, int] = {
    LeagueTier.A: 15_000,
    LeagueTier.B: 6_000,
    LeagueTier.C: 2_500,
    LeagueTier.D: 1_200,
    LeagueTier.E: 600,
}
# Tier de la marca (1..5) segun el nivel de la liga.
_TIER_RANK: dict[LeagueTier, int] = {
    LeagueTier.E: 1, LeagueTier.D: 2, LeagueTier.C: 3, LeagueTier.B: 4, LeagueTier.A: 5,
}


class SponsorGenerator:
    """Crea marcas y ofertas de contrato acordes al nivel del club."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()

    def _brand(self, tier: LeagueTier) -> Sponsor:
        rng = self._rng
        name = rng.choice(sponsor_data.BRAND_ROOTS) + rng.choice(sponsor_data.BRAND_SUFFIXES)
        sector = rng.choice(sponsor_data.SECTORS)
        return Sponsor(name=name.capitalize(), sector=sector, tier=_TIER_RANK[tier])

    def _noise(self, value: float) -> int:
        """Ruido +/-15% para que dos ofertas del mismo tier no sean identicas."""
        return round(value * self._rng.uniform(0.85, 1.15))

    def offers(self, tier: LeagueTier, n: int = 3) -> list[SponsorContract]:
        """Devuelve `n` ofertas variadas para un club de la liga `tier`."""
        base = _TIER_BASE_PAY[tier]
        # Plantillas: (semanas, factor_pago, signing_x, promo_x, streak_x, streak_len).
        templates = [
            (12, 1.40, 3, 0, 0, 0),     # corta y bien paga, sin bonus
            (26, 1.00, 2, 20, 0, 0),    # media, con bonus por ascenso
            (52, 0.75, 1, 15, 6, 3),    # larga, pago menor + bonus por racha/ascenso
        ]
        out: list[SponsorContract] = []
        for i in range(n):
            weeks, pay_f, sign_x, promo_x, streak_x, streak_len = templates[i % len(templates)]
            weekly = self._noise(base * pay_f)
            out.append(SponsorContract(
                sponsor=self._brand(tier),
                weeks_total=weeks,
                weeks_remaining=weeks,
                weekly_pay=weekly,
                signing_bonus=self._noise(base * sign_x),
                promotion_bonus=self._noise(base * promo_x) if promo_x else 0,
                streak_bonus=self._noise(base * streak_x) if streak_x else 0,
                streak_len=streak_len,
            ))
        return out

    def auto(self, tier: LeagueTier) -> SponsorContract:
        """Una oferta equilibrada (la media) para un club IA."""
        return self.offers(tier, 3)[1]
