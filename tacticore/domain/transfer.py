"""Entidad de negociacion: una oferta de transferencia del jugador humano.

El jugador hace ofertas por futbolistas listados en el mercado; el club vendedor
(IA) responde en el loop diario: aceptar, contraofertar (una ronda) o rechazar. Las
ofertas son SIEMPRE del club del jugador (el comprador), asi que no se guarda el
comprador. El estado vive en `GameState.offers`.
"""

from dataclasses import dataclass

from .player import Player

# Estados posibles de una oferta.
PENDING = "pending"       # esperando respuesta del vendedor
COUNTERED = "countered"   # el vendedor contraoferto; espera al humano
ACCEPTED = "accepted"     # aceptada (la transferencia ya se ejecuto)
REJECTED = "rejected"     # rechazada
WITHDRAWN = "withdrawn"   # el humano la retiro


@dataclass
class TransferOffer:
    """Una oferta del jugador por un futbolista listado."""

    target: Player
    amount: int
    status: str = PENDING
    counter_amount: int = 0   # monto de la contraoferta (si status == COUNTERED)
    days_left: int = 1        # dias hasta que el vendedor responda

    @property
    def open(self) -> bool:
        """True si sigue viva (esperando respuesta o decision del humano)."""
        return self.status in (PENDING, COUNTERED)
