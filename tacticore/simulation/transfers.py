"""Mercado de pases: listar jugadores, ofertar/negociar y la actividad de la IA.

Funciones PURAS sobre el estado (sin UI). El jugador humano LISTA sus futbolistas
(les pone `asking_price`) y hace OFERTAS por los listados; el club vendedor (IA)
responde en el loop diario (aceptar / contraoferta de una ronda / rechazar). Ademas,
una vez por semana la IA hace altas y bajas acotadas (`ai_market_step`) para que el
mercado se sienta vivo. Todo determinista con el `random.Random` que se pasa.
"""

import random

from ..domain.club import Club
from ..domain.player import Player
from ..domain.positions import is_goalkeeper
from ..domain.transfer import (
    ACCEPTED, COUNTERED, PENDING, REJECTED, WITHDRAWN, TransferOffer)
from . import notifications as notif
from .economy import asking_price
from .finance_log import record_movement

MIN_SQUAD = 14   # nadie vende por debajo de esto
MAX_SQUAD = 24   # nadie compra por encima de esto
_COUNTER_FLOOR = 0.85  # ofertas por debajo del 85% del precio se rechazan


def _all_clubs(game) -> list[Club]:
    return [c for co in game.countries for lg in co.leagues for c in lg.clubs]


def owner_club(game, player: Player) -> Club | None:
    """Club al que pertenece `player` ahora mismo (o None si ya no juega)."""
    for club in _all_clubs(game):
        if player in club.players:
            return club
    return None


# --- Listar / quitar de venta (acciones del jugador) ---
def list_player(player: Player, price: int | None = None, today=None) -> None:
    """Pone un jugador en venta (precio sugerido si no se pasa uno)."""
    player.asking_price = price if price is not None else asking_price(player, today)


def unlist_player(player: Player) -> None:
    player.asking_price = None


def all_listings(game) -> list[tuple[Player, Club]]:
    """Todos los jugadores en venta del mundo, con su club."""
    out = []
    for club in _all_clubs(game):
        for p in club.players:
            if p.asking_price is not None:
                out.append((p, club))
    return out


# --- Ofertas del jugador ---
def make_offer(game, player: Player, amount: int) -> TransferOffer:
    """Crea (o reemplaza) la oferta del jugador por `player`."""
    game.offers = [o for o in game.offers if o.target is not player]
    offer = TransferOffer(target=player, amount=amount)
    game.offers.append(offer)
    return offer


def accept_counter(game, offer: TransferOffer) -> bool:
    """El jugador acepta una contraoferta: ejecuta la compra si puede."""
    if offer.status != COUNTERED:
        return False
    seller = owner_club(game, offer.target)
    if seller is None or not _can_buy(game.player_club, seller, offer.counter_amount):
        offer.status = REJECTED
        return False
    execute_transfer(game, game.player_club, seller, offer.target, offer.counter_amount)
    offer.status = ACCEPTED
    return True


def withdraw_offer(offer: TransferOffer) -> None:
    offer.status = WITHDRAWN


def resolve_offers(game) -> None:
    """Baja un dia las ofertas pendientes y hace decidir al vendedor las que vencen."""
    buyer = game.player_club
    for offer in game.offers:
        if offer.status != PENDING:
            continue
        offer.days_left -= 1
        if offer.days_left > 0:
            continue
        seller = owner_club(game, offer.target)
        ask = offer.target.asking_price
        if seller is None or ask is None:  # ya no esta a la venta
            offer.status = REJECTED
        elif offer.amount >= ask and _can_buy(buyer, seller, offer.amount):
            execute_transfer(game, buyer, seller, offer.target, offer.amount)
            offer.status = ACCEPTED
        elif offer.amount >= ask * _COUNTER_FLOOR:
            offer.status = COUNTERED
            offer.counter_amount = round((offer.amount + ask) / 2)
        else:
            offer.status = REJECTED


# --- Ejecucion de una transferencia ---
def _can_buy(buyer: Club, seller: Club, fee: int) -> bool:
    return (buyer is not None and buyer.capital >= fee
            and len(buyer.players) < MAX_SQUAD and len(seller.players) > MIN_SQUAD)


def _next_shirt(club: Club) -> int:
    used = {p.shirt_number for p in club.players if p.shirt_number}
    n = 1
    while n in used:
        n += 1
    return n


def execute_transfer(game, buyer: Club, seller: Club, player: Player, fee: int) -> bool:
    """Mueve al jugador y la plata; limpia venta/ofertas. Devuelve si se concreto."""
    if player not in seller.players or len(seller.players) <= MIN_SQUAD:
        return False
    if len(buyer.players) >= MAX_SQUAD or buyer.capital < fee:
        return False
    seller.players.remove(player)
    buyer.players.append(player)
    seller.capital += fee
    buyer.capital -= fee
    player.asking_price = None
    player.shirt_number = _next_shirt(buyer)
    player.origin_club = player.origin_club or seller.name
    # Cualquier oferta del humano sobre este jugador queda sin efecto.
    for o in game.offers:
        if o.target is player and o.status in (PENDING, COUNTERED):
            o.status = REJECTED
    _report_transfer(game, buyer, seller, player, fee)
    return True


def _money(amount: int) -> str:
    return "$" + f"{amount:,}".replace(",", ".")


def _report_transfer(game, buyer: Club, seller: Club, player: Player, fee: int) -> None:
    """Si el club del jugador entra en la operacion, deja movimiento y notificacion."""
    pc = game.player_club
    when = game.calendar.current_date
    if buyer is pc:
        record_movement(pc, when, f"Fichaje de {player.full_name}", -fee)
        notif.notify(
            game, "Fichaje concretado",
            f"Incorporamos a {player.full_name} desde {seller.name} por {_money(fee)}.",
            notif.MARKET,
        )
    elif seller is pc:
        record_movement(pc, when, f"Venta de {player.full_name}", fee)
        notif.notify(
            game, "Venta concretada",
            f"Vendimos a {player.full_name} a {buyer.name} por {_money(fee)}.",
            notif.MARKET,
        )


# --- Actividad semanal de la IA ---
def _weakest_surplus(club: Club) -> Player | None:
    """El jugador de campo de menor overall (candidato a vender)."""
    outfield = [p for p in club.players if not is_goalkeeper(p.position)]
    return min(outfield, key=lambda p: p.overall) if outfield else None


def _fits(club: Club, player: Player) -> bool:
    """El club 'necesita' esa posicion (pocos jugadores o mejora al peor)."""
    same = [p for p in club.players if p.position is player.position]
    if len(same) < 2:
        return True
    return player.overall > min(p.overall for p in same)


def ai_market_step(game, rng: random.Random) -> int:
    """Altas y bajas acotadas de la IA (una vez por semana). Devuelve # de compras."""
    clubs = [c for c in _all_clubs(game) if c is not game.player_club]
    # Vendedores: ~3% de clubes con plantel de sobra y sin nada listado listan uno.
    for club in clubs:
        if rng.random() >= 0.03:
            continue
        if len(club.players) <= MIN_SQUAD:
            continue
        if any(p.asking_price is not None for p in club.players):
            continue
        surplus = _weakest_surplus(club)
        if surplus is not None:
            surplus.asking_price = asking_price(surplus)
    # Compradores: ~3% de clubes compran directo el mejor listado que les sirva.
    listings = all_listings(game)
    buys = 0
    for club in clubs:
        if rng.random() >= 0.03:
            continue
        if len(club.players) >= MAX_SQUAD:
            continue
        budget = club.capital * 0.5
        candidates = [
            (p, s) for (p, s) in listings
            if s is not club and p.asking_price <= budget
            and _fits(club, p) and len(s.players) > MIN_SQUAD
        ]
        if not candidates:
            continue
        player, seller = max(candidates, key=lambda ps: ps[0].overall)
        if execute_transfer(game, club, seller, player, player.asking_price):
            listings = [(p, s) for (p, s) in listings if p is not player]
            buys += 1
    return buys
