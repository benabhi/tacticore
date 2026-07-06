"""Fin de temporada: ascensos y descensos entre las ligas de un pais.

Cuando se juega la ultima fecha de TODAS las ligas, la temporada termina y se
reordena la piramide de cada pais: los `_PROMOTE_COUNT` primeros de cada liga
suben una division y los ultimos bajan una (la liga A no sube, la E no baja). Es
el eje de progresion del jugador: salir arriba en su liga lo asciende de tier.

Tras reordenar, se regenera el fixture de todas las ligas (y los amistosos del
jugador) para la temporada nueva, arrancando tras un receso de `_OFFSEASON_GAP`
dias. Todo determinista por semilla. Sin UI: deja notificaciones en el estado.
"""

from datetime import date, timedelta

from ..core.rng import new_rng
from ..domain.enums import LeagueTier, MatchKind
from . import notifications as notif

# Cuantos clubes ascienden/descienden por frontera (de 8 por liga -> 25% de recambio).
_PROMOTE_COUNT = 2
# Dias de receso entre el fin de una temporada y el arranque de la siguiente.
_OFFSEASON_GAP = 14

# Orden de calidad de los tiers (A mejor .. E peor), para ordenar las ligas.
_TIER_ORDER = list(LeagueTier)  # [A, B, C, D, E]


def season_over(game) -> bool:
    """True si ya se jugaron TODOS los partidos de liga de TODAS las ligas.

    Si alguna liga aun no tiene fixture, la temporada no se considera terminada.
    Los amistosos del jugador (game.friendlies) no cuentan."""
    any_matches = False
    for country in game.countries:
        for league in country.leagues:
            if not league.matches:
                return False
            for m in league.matches:
                if m.kind is MatchKind.LEAGUE:
                    any_matches = True
                    if not m.played:
                        return False
    return any_matches


def maybe_end_season(game, rng) -> bool:
    """Si la temporada termino, corre la transicion. Devuelve si la corrio."""
    if not season_over(game):
        return False
    run_season_transition(game, rng)
    return True


def _player_standing(game):
    """(tier actual, posicion, tamano de liga) del club del jugador, o None."""
    from .season import compute_standings

    pc = game.player_club
    league = game.player_league
    if pc is None or league is None:
        return None
    table = compute_standings(league)
    for i, s in enumerate(table, start=1):
        if s.club is pc:
            return pc.tier, i, len(table)
    return pc.tier, len(table), len(table)


def run_season_transition(game, rng, today: date | None = None) -> None:
    """Aplica ascensos/descensos en todos los paises y arma la temporada siguiente."""
    from .season import compute_standings, ensure_player_friendlies, generate_league_fixture

    today = today or game.calendar.current_date
    before = _player_standing(game)  # antes de mover, para notificar al jugador
    game.season += 1

    for country in game.countries:
        leagues = sorted(country.leagues, key=lambda lg: _TIER_ORDER.index(lg.tier))
        # Snapshot de las tablas ANTES de mover a nadie.
        standings = {lg.tier: compute_standings(lg) for lg in leagues}
        # Cada movimiento: (club, liga_origen, liga_destino). Los conjuntos son
        # disjuntos (top-N vs bottom-N de una misma liga no se solapan).
        moves = []
        for i in range(len(leagues) - 1):
            upper, lower = leagues[i], leagues[i + 1]
            relegated = [s.club for s in standings[upper.tier][-_PROMOTE_COUNT:]]
            promoted = [s.club for s in standings[lower.tier][:_PROMOTE_COUNT]]
            moves += [(c, upper, lower) for c in relegated]
            moves += [(c, lower, upper) for c in promoted]
        # Sacar a todos de su liga vieja y meterlos en la nueva (setear su tier).
        for club, src, _dst in moves:
            src.clubs.remove(club)
        for club, _src, dst in moves:
            dst.clubs.append(club)
            club.tier = dst.tier

    # Fixture nuevo para todas las ligas + amistosos del jugador (temporada nueva).
    new_start = today + timedelta(days=_OFFSEASON_GAP)
    index = 0
    for country in game.countries:
        for league in country.leagues:
            league.matches = []
            generate_league_fixture(
                league, new_rng(game.seed + game.season * 997 + index), new_start)
            index += 1
    game.friendlies = []
    ensure_player_friendlies(game, new_start)

    _notify_player(game, before)


def _notify_player(game, before) -> None:
    """Notifica al jugador su posicion final y si ascendio/descendio/se mantuvo."""
    pc = game.player_club
    if pc is None or before is None:
        return
    old_tier, pos, size = before
    new_tier = pc.tier
    old_rank, new_rank = _TIER_ORDER.index(old_tier), _TIER_ORDER.index(new_tier)
    if new_rank < old_rank:      # indice menor = mejor liga
        subject = "Ascenso de division"
        body = (f"Terminaste {pos} de {size} en la liga {old_tier.value}. "
                f"ASCENSO a la liga {new_tier.value}!")
    elif new_rank > old_rank:
        subject = "Descenso de division"
        body = (f"Terminaste {pos} de {size} en la liga {old_tier.value}. "
                f"Descenso a la liga {new_tier.value}.")
    else:
        subject = "Fin de temporada"
        body = (f"Terminaste {pos} de {size} en la liga {old_tier.value}. "
                f"Seguis en la misma division.")
    notif.notify(game, subject, body, notif.GENERAL)
