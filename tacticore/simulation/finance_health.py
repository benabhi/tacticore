"""Salud financiera del club del jugador: insolvencia, ventas forzadas y sancion.

Si el club se gestiona mal y la caja queda muy en rojo, el club NO desaparece (no es
game over): primero se venden jugadores por necesidad (ventas forzadas) para cubrir la
deuda, y si al terminar la temporada sigue insolvente, sufre una SANCION deportiva
(descenso forzado). Asi una mala administracion se paga, pero el club sigue.

Funciones puras sobre el estado (sin UI). El descenso forzado de fin de temporada lo
dispara `promotion.run_season_transition`; las ventas forzadas, el cierre economico
semanal (`daily._weekly_economy`).
"""

from datetime import date

from .economy import player_value
from .finance_log import record_movement
from .transfers import MIN_SQUAD
from . import notifications as notif


def is_insolvent(club) -> bool:
    """True si el club esta en rojo (dispara ventas forzadas / sancion)."""
    return club.capital < 0


def enforce_solvency(game, today: date) -> None:
    """Vende jugadores (los de menor valor) si la caja quedo en rojo.

    Vende de a uno, del menos valioso al mas valioso, hasta recuperar la caja (>=0) o
    tocar el minimo de plantel (`MIN_SQUAD`). Cada venta deja movimiento y notificacion.
    Solo actua sobre el club del jugador (el unico que lleva libro/caja real). El
    respaldo si aun asi queda en rojo es el descenso administrativo de fin de temporada."""
    club = game.player_club
    if club is None or not is_insolvent(club):
        return
    sold = []
    while club.capital < 0 and len(club.players) > MIN_SQUAD:
        victim = min(club.players, key=lambda p: player_value(p, today))
        fee = player_value(victim, today)
        club.players.remove(victim)
        club.capital += fee
        record_movement(club, today, f"Venta forzada: {victim.full_name}", fee)
        sold.append((victim, fee))
    if sold:
        detail = ", ".join(f"{p.full_name} (${fee:,})".replace(",", ".") for p, fee in sold)
        tail = ("" if club.capital >= 0 else
                " Aun asi la caja sigue en rojo: cuida las finanzas.")
        notif.notify(
            game, "Ventas forzadas por deuda",
            f"Para cubrir la deuda el club tuvo que vender: {detail}.{tail}",
            notif.FINANCE,
        )
