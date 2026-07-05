"""Registro de notificaciones del juego (novedades para el manager).

La simulacion deja notificaciones (subject + message) cuando pasa algo de interes
para el jugador: cierre economico, resultado de un partido, fichajes, resumen de
entrenamiento, etc. La UI las muestra en Oficina > Notificaciones y cuenta las no
leidas en la barra superior. Funciones puras sobre el estado (sin UI).
"""

from ..domain.notification import Notification

# Tope de notificaciones guardadas (se descartan las mas viejas). Evita que un
# save largo acumule miles de filas.
_MAX = 300

# Categorias conocidas (para colorear en la UI). Texto libre igual sirve.
FINANCE = "finanzas"
MATCH = "partido"
MARKET = "mercado"
TRAINING = "entrenamiento"
GENERAL = "general"


def notify(game, subject: str, message: str, category: str = GENERAL) -> Notification:
    """Agrega una notificacion fechada al dia actual del juego."""
    n = Notification(
        subject=subject, message=message,
        date=game.calendar.current_date, category=category,
    )
    game.notifications.append(n)
    if len(game.notifications) > _MAX:
        del game.notifications[: len(game.notifications) - _MAX]
    return n


def unread_count(game) -> int:
    """Cantidad de notificaciones sin leer."""
    return sum(1 for n in game.notifications if not n.read)


def recent(game, count: int = 5) -> list[Notification]:
    """Las ultimas `count` notificaciones, de la mas nueva a la mas vieja."""
    return list(reversed(game.notifications[-count:]))


def all_newest_first(game) -> list[Notification]:
    """Todas las notificaciones, de la mas nueva a la mas vieja."""
    return list(reversed(game.notifications))


def mark_all_read(game) -> None:
    """Marca todas las notificaciones como leidas."""
    for n in game.notifications:
        n.read = True
