"""Patrocinadores por oferta-evento: cupos por tier, calidad y ciclo de ofertas.

El club tiene CUPOS de patrocinador segun su liga (E1 D2 C3 B4 A5). El primero se
firma al crear el club; los cupos que se liberan (cuando un contrato termina) o se
desbloquean (al ascender) se llenan con OFERTAS que llegan como notificaciones-evento
(`kind=sponsor_offer`): el manager las abre y acepta o rechaza. Cada oferta caduca en
una ventana de decision. La calidad de las ofertas depende del Director financiero
(empleado) y de las construcciones comerciales.

Logica pura (sin Textual). El ciclo lo corre `daily.advance_day` una vez por semana.
"""

from datetime import date, timedelta

from ..domain.enums import EmployeeRole, LeagueTier
from ..domain.sponsor import Sponsor, SponsorContract
from .finance_log import record_movement
from . import notifications as notif
from . import staff

# Cupos de patrocinador por nivel de liga (+1 por liga hasta 5 en primera).
_SLOTS: dict[LeagueTier, int] = {
    LeagueTier.E: 1, LeagueTier.D: 2, LeagueTier.C: 3, LeagueTier.B: 4, LeagueTier.A: 5,
}
_OFFER_WINDOW_DAYS = 21   # ventana de decision de una oferta antes de caducar
_QUALITY_CAP = 0.60       # calidad extra maxima (offer_quality en [1.0, 1.6])
_COMMERCIAL_PER_LEVEL = 0.03  # cuanto suma cada nivel de instalacion comercial
_COMMERCIAL_CAP = 0.35


def _money(amount: int) -> str:
    return "$" + f"{amount:,}".replace(",", ".")


def slots_for_tier(tier: LeagueTier) -> int:
    """Cupos de patrocinador del club segun su liga."""
    return _SLOTS[tier]


def active_sponsors(club) -> list[SponsorContract]:
    return [s for s in club.sponsors if s.active]


def free_slots(club) -> int:
    """Cupos de patrocinador sin cubrir por un contrato activo."""
    return max(0, slots_for_tier(club.tier) - len(active_sponsors(club)))


def _commercial_factor(club) -> float:
    """Aporte de las construcciones comerciales a la calidad de las ofertas."""
    from . import facilities as fac

    total = sum(lv for fid, lv in club.facilities.items()
                if fac.spec(fid).category == "Comercial")
    return min(_COMMERCIAL_CAP, total * _COMMERCIAL_PER_LEVEL)


def offer_quality(club) -> float:
    """Multiplicador (1.0-1.6) de calidad de una oferta: director financiero + comercio."""
    extra = staff.finance_income_bonus(club) + _commercial_factor(club)
    return 1.0 + min(_QUALITY_CAP, extra)


def _make_offer(club, rng) -> SponsorContract:
    """Genera un contrato ofrecido, escalado por la calidad del club."""
    from ..generators.sponsor_generator import SponsorGenerator

    contract = rng.choice(SponsorGenerator(rng).offers(club.tier, 3))
    q = offer_quality(club)
    contract.weekly_pay = round(contract.weekly_pay * q)
    contract.signing_bonus = round(contract.signing_bonus * q)
    contract.promotion_bonus = round(contract.promotion_bonus * q)
    contract.streak_bonus = round(contract.streak_bonus * q)
    return contract


def _payload(contract: SponsorContract, expires: date) -> dict:
    s = contract.sponsor
    return {
        "name": s.name, "sector": s.sector, "tier": s.tier,
        "weeks_total": contract.weeks_total, "weekly_pay": contract.weekly_pay,
        "signing_bonus": contract.signing_bonus,
        "promotion_bonus": contract.promotion_bonus,
        "streak_bonus": contract.streak_bonus, "streak_len": contract.streak_len,
        "expires": expires.isoformat(),
    }


def contract_from_payload(p: dict) -> SponsorContract:
    """Reconstruye el contrato de una oferta aceptada (arranca con las semanas llenas)."""
    return SponsorContract(
        sponsor=Sponsor(name=p["name"], sector=p["sector"], tier=p["tier"]),
        weeks_total=p["weeks_total"], weeks_remaining=p["weeks_total"],
        weekly_pay=p["weekly_pay"], signing_bonus=p["signing_bonus"],
        promotion_bonus=p["promotion_bonus"], streak_bonus=p["streak_bonus"],
        streak_len=p["streak_len"],
    )


def _pending_offer(game):
    """La oferta de patrocinio pendiente del jugador (o None): solo hay una a la vez."""
    for n in notif.pending_events(game):
        if n.kind == notif.EVENT_SPONSOR_OFFER:
            return n
    return None


def tick_sponsor_offers(game, today: date, rng) -> None:
    """Corre el ciclo semanal: caduca la oferta vencida, limpia contratos terminados y,
    si hay cupo libre y no hay oferta pendiente, genera una nueva oferta-evento."""
    club = game.player_club
    if club is None:
        return
    # Caducar la oferta pendiente si paso su ventana.
    pending = _pending_offer(game)
    if pending is not None and today > date.fromisoformat(pending.payload["expires"]):
        notif.resolve(game, pending, "expired")
        pending.subject = "Oferta de patrocinio vencida"
        pending.message = f"{pending.payload['name']} retiro su oferta de patrocinio."
        pending = None
    # Sacar de la lista los contratos ya terminados (liberan su cupo).
    club.sponsors[:] = [s for s in club.sponsors if s.active]
    # Nueva oferta si queda cupo y no hay ninguna pendiente.
    if pending is None and free_slots(club) > 0:
        contract = _make_offer(club, rng)
        expires = today + timedelta(days=_OFFER_WINDOW_DAYS)
        s = contract.sponsor
        notif.notify(
            game, f"Oferta de patrocinio: {s.name}",
            f"{s.name} ({s.sector}) ofrece {_money(contract.weekly_pay)}/sem por "
            f"{contract.weeks_total} semanas. Vence el {expires.strftime('%d-%m-%Y')}. "
            f"Abri la oferta para aceptar o rechazar.",
            notif.FINANCE, kind=notif.EVENT_SPONSOR_OFFER,
            payload=_payload(contract, expires),
        )


def accept_offer(game, n) -> bool:
    """Acepta la oferta `n`: firma el contrato y acredita el bono de firma."""
    club = game.player_club
    if club is None or not n.is_pending_event:
        return False
    if free_slots(club) <= 0:  # ya no hay cupo (se ocupo por otra via)
        notif.resolve(game, n, "expired")
        return False
    contract = contract_from_payload(n.payload)
    club.sponsors.append(contract)
    club.capital += contract.signing_bonus
    record_movement(club, game.calendar.current_date,
                    f"Firma patrocinio {contract.sponsor.name}", contract.signing_bonus)
    notif.resolve(game, n, "accepted")
    notif.notify(
        game, "Patrocinio firmado",
        f"Firmaste con {contract.sponsor.name}: {_money(contract.weekly_pay)}/sem por "
        f"{contract.weeks_total} semanas.", notif.FINANCE)
    return True


def reject_offer(game, n) -> None:
    """Rechaza la oferta `n` (el cupo sigue libre: la proxima semana llega otra)."""
    if n.is_pending_event:
        notif.resolve(game, n, "rejected")
