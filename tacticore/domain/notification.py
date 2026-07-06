"""Entidad Notificacion: una novedad del juego para el manager.

El juego va dejando notificaciones (tipo registro) a medida que pasan cosas de
interes: cierre economico, resultado de un partido, un fichaje, el resumen de
entrenamiento, etc. El jugador las lee en la seccion Oficina > Notificaciones; las
no leidas se cuentan en la barra superior para que no se le pase nada por alto.

Cada notificacion tiene un `subject` (titulo corto) y un `message` (detalle), la
fecha en que se genero, una `category` (para colorear/filtrar) y si ya fue leida.

Ademas de las informativas, hay EVENTOS accionables: notificaciones con un `kind`
(ej. "sponsor_offer"), un `payload` con los datos del evento y un `status`
("pending" hasta que el manager decide; luego "accepted"/"rejected"/"expired"). El
sistema es generico: se despacha por `kind` y sirve para futuros eventos aleatorios.
"""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Notification:
    """Una novedad para el manager (subject + message), con fecha y estado."""

    subject: str
    message: str
    date: date
    category: str = "general"  # finanzas, partido, mercado, entrenamiento, ...
    read: bool = False
    kind: str = ""             # ""=info; "sponsor_offer"=evento accionable
    payload: dict | None = None  # datos del evento (ej. la oferta de patrocinio)
    status: str = ""           # "pending"/"accepted"/"rejected"/"expired" (solo eventos)

    @property
    def is_pending_event(self) -> bool:
        """True si es un evento que el manager todavia no resolvio."""
        return bool(self.kind) and self.status == "pending"
