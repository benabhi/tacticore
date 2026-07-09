"""Registro de notificaciones del juego (novedades para el manager).

La simulacion deja notificaciones (subject + message) cuando pasa algo de interes
para el jugador: cierre economico, resultado de un partido, fichajes, resumen de
entrenamiento, etc. La UI las muestra en Club > Notificaciones y cuenta las no
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
SQUAD = "plantel"      # lesiones, tarjetas, suspensiones
GENERAL = "general"

# Tipos de EVENTO accionable (kind). "" = notificacion informativa comun.
EVENT_SPONSOR_OFFER = "sponsor_offer"


def notify(game, subject: str, message: str, category: str = GENERAL,
           kind: str = "", payload: dict | None = None) -> Notification:
    """Agrega una notificacion fechada al dia actual del juego.

    Con `kind` (ej. EVENT_SPONSOR_OFFER) y `payload` crea un EVENTO accionable que
    arranca en status "pending" hasta que el manager lo resuelva."""
    n = Notification(
        subject=subject, message=message,
        date=game.calendar.current_date, category=category,
        kind=kind, payload=payload, status="pending" if kind else "",
    )
    game.notifications.append(n)
    _trim(game)
    return n


def _trim(game) -> None:
    """Descarta las mas viejas si se pasa de `_MAX`, pero NUNCA un evento pendiente."""
    excess = len(game.notifications) - _MAX
    if excess <= 0:
        return
    keep = [n for n in game.notifications if n.is_pending_event]
    droppable = [n for n in game.notifications if not n.is_pending_event]
    del droppable[:excess]
    # Reconstruye respetando el orden original (por fecha de llegada).
    survivors = set(id(n) for n in keep) | set(id(n) for n in droppable)
    game.notifications[:] = [n for n in game.notifications if id(n) in survivors]


def pending_events(game) -> list[Notification]:
    """Eventos accionables que el manager todavia no resolvio (mas nuevos primero)."""
    return [n for n in reversed(game.notifications) if n.is_pending_event]


def resolve(game, n: Notification, status: str) -> None:
    """Cierra un evento ('accepted'/'rejected'/'expired') y lo marca leido."""
    n.status = status
    n.read = True


def unread_count(game) -> int:
    """Cantidad de notificaciones sin leer (incluye eventos pendientes)."""
    return sum(1 for n in game.notifications if not n.read)


def recent(game, count: int = 5) -> list[Notification]:
    """Las ultimas `count` notificaciones, de la mas nueva a la mas vieja."""
    return list(reversed(game.notifications[-count:]))


def all_newest_first(game) -> list[Notification]:
    """Todas las notificaciones, de la mas nueva a la mas vieja."""
    return list(reversed(game.notifications))


def mark_all_read(game) -> None:
    """Marca leidas las notificaciones, salvo los eventos PENDIENTES (siguen avisando
    en la barra hasta que el manager los resuelva)."""
    for n in game.notifications:
        if not n.is_pending_event:
            n.read = True
