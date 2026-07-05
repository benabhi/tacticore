"""Disciplina y lesiones del club del jugador (tarjetas, suspensiones, bajas).

Al jugarse un partido del club del jugador se tira, jugador por jugador del once
que jugo, por lesion (en cualquier partido) y por tarjetas (solo en partidos de
LIGA). Reglas:
- 2 amarillas ACUMULADAS -> se pierde el proximo partido de liga (y las amarillas
  se resetean). Roja -> se pierde el proximo partido.
- La suspension se "sirve" perdiendose ese partido de liga: al jugarse la fecha,
  `serve_suspensions` descuenta a los suspendidos (que no jugaron).
- Las lesiones se recuperan solas al llegar su fecha de alta (`recover_injuries`).

Los lesionados y suspendidos no estan disponibles (`Player.is_available`) y por eso
no los eligen ni `pick_lineup` ni las pantallas de tactica. Todo es determinista
con el `random.Random` que se pasa. Solo se modela el club del jugador (a la IA no
le hace falta). Sin UI: deja NOTIFICACIONES en el estado del juego.
"""

import random
from datetime import date, timedelta

from ..domain.club import Club
from ..domain.enums import InjurySeverity, InjuryType, MatchKind
from ..domain.injury import Injury
from ..domain.player import Player
from . import notifications as notif
from . import staff
from .match.formation import FORMATION_11, get_formation, pick_lineup

# Probabilidades por jugador y por partido (tuneables).
_INJURY_BASE = 0.015  # escalado por la propension a lesionarse del jugador
_YELLOW_BASE = 0.10   # amarilla en un partido de liga
_RED_BASE = 0.006     # roja en un partido de liga

# Gravedad de la lesion: pesos y rango de semanas de baja.
_SEVERITY_WEIGHTS = [
    (InjurySeverity.MINOR, 0.60),
    (InjurySeverity.MODERATE, 0.30),
    (InjurySeverity.SEVERE, 0.10),
]
_SEVERITY_WEEKS = {
    InjurySeverity.MINOR: (1, 2),
    InjurySeverity.MODERATE: (3, 5),
    InjurySeverity.SEVERE: (6, 12),
}

# Nombre en espanol del tipo de lesion para el texto de la notificacion (la UI
# tiene su propio mapa en player_labels; aca se replica para no importar UI).
_TYPE_ES = {
    InjuryType.KNOCK: "golpe", InjuryType.MUSCLE: "muscular",
    InjuryType.HAMSTRING: "isquiotibial", InjuryType.ANKLE: "tobillo",
    InjuryType.KNEE: "rodilla", InjuryType.HEAD: "conmocion",
    InjuryType.FRACTURE: "fractura",
}


def available_xi(club: Club, match) -> list[Player]:
    """Los 11 que jugaron: la alineacion automatica sobre los disponibles."""
    formation = get_formation(match.tactic.formation) if match.tactic else FORMATION_11
    return pick_lineup(club, formation, available_only=True)


def _weighted_severity(rng: random.Random) -> InjurySeverity:
    r = rng.random()
    acc = 0.0
    for severity, weight in _SEVERITY_WEIGHTS:
        acc += weight
        if r < acc:
            return severity
    return InjurySeverity.MINOR


def generate_injury(rng: random.Random, today: date,
                    weeks_factor: float = 1.0) -> tuple[Injury, int]:
    """Crea una lesion al azar y devuelve (lesion, semanas de baja).

    `weeks_factor` (<=1) acorta la baja: lo aporta el medico del club (recuperacion
    mas rapida). La baja nunca baja de 1 semana."""
    itype = rng.choice(list(InjuryType))
    severity = _weighted_severity(rng)
    lo, hi = _SEVERITY_WEEKS[severity]
    weeks = max(1, round(rng.randint(lo, hi) * weeks_factor))
    injury = Injury(
        type=itype, severity=severity, start_date=today,
        expected_return=today + timedelta(weeks=weeks),
    )
    return injury, weeks


def roll_match_events(game, club: Club, xi: list[Player], is_league: bool,
                      today: date, rng: random.Random) -> None:
    """Tira lesiones (siempre) y tarjetas (solo liga) para el once que jugo.

    Deja notificaciones en el estado. Un jugador que se lesiona no recibe ademas
    tarjeta en el mismo partido."""
    # El cuerpo medico del club baja la probabilidad y acorta las bajas.
    inj_factor = staff.injury_factor(club)
    weeks_factor = staff.injury_weeks_factor(club)
    for p in xi:
        if p.injury is None:
            p_inj = _INJURY_BASE * (0.5 + p.injury_proneness / 100) * inj_factor
            if rng.random() < p_inj:
                injury, weeks = generate_injury(rng, today, weeks_factor)
                p.injury = injury
                notif.notify(
                    game, "Lesion en el plantel",
                    f"{p.full_name} sufrio una lesion ({_TYPE_ES[injury.type]}) y "
                    f"estara ~{weeks} semana(s) de baja.",
                    notif.SQUAD,
                )
                continue
        if not is_league:
            continue
        r = rng.random()
        if r < _RED_BASE:
            p.matches_suspended += 1
            notif.notify(
                game, "Tarjeta roja",
                f"{p.full_name} vio la roja y se pierde el proximo partido de liga.",
                notif.SQUAD,
            )
        elif r < _RED_BASE + _YELLOW_BASE:
            p.yellow_cards += 1
            if p.yellow_cards >= 2:
                p.yellow_cards = 0
                p.matches_suspended += 1
                notif.notify(
                    game, "Suspension por amarillas",
                    f"{p.full_name} llego a 2 amarillas y se pierde el proximo "
                    f"partido de liga.",
                    notif.SQUAD,
                )


def serve_suspensions(club: Club) -> None:
    """Descuenta un partido a los suspendidos (se lo perdieron al no jugar la
    fecha de liga). Se llama despues de un partido de LIGA del club."""
    for p in club.players:
        if p.matches_suspended > 0:
            p.matches_suspended -= 1


def recover_injuries(game, today: date) -> None:
    """Da de alta a los lesionados del club del jugador cuya baja ya vencio."""
    club = game.player_club
    if club is None:
        return
    for p in club.players:
        if p.injury is not None and today >= p.injury.expected_return:
            p.injury_history.append(p.injury)
            p.injury = None
            notif.notify(
                game, "Recuperacion",
                f"{p.full_name} se recupero de su lesion y esta disponible.",
                notif.SQUAD,
            )


def apply_player_match_discipline(game, match, today: date,
                                  rng: random.Random) -> None:
    """Aplica la disciplina tras un partido del club del jugador: sirve las
    suspensiones (si es liga) y tira lesiones/tarjetas para el once que jugo."""
    pc = game.player_club
    if pc is None or pc not in (match.home, match.away):
        return
    is_league = match.kind is MatchKind.LEAGUE
    xi = available_xi(pc, match)
    if is_league:
        serve_suspensions(pc)
    roll_match_events(game, pc, xi, is_league, today, rng)
