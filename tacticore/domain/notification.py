"""Entidad Notificacion: una novedad del juego para el manager.

El juego va dejando notificaciones (tipo registro) a medida que pasan cosas de
interes: cierre economico, resultado de un partido, un fichaje, el resumen de
entrenamiento, etc. El jugador las lee en la seccion Oficina > Notificaciones; las
no leidas se cuentan en la barra superior para que no se le pase nada por alto.

Cada notificacion tiene un `subject` (titulo corto) y un `message` (detalle), la
fecha en que se genero, una `category` (para colorear/filtrar) y si ya fue leida.
"""

from dataclasses import dataclass
from datetime import date


@dataclass
class Notification:
    """Una novedad para el manager (subject + message), con fecha y estado."""

    subject: str
    message: str
    date: date
    category: str = "general"  # finanzas, partido, mercado, entrenamiento, ...
    read: bool = False
