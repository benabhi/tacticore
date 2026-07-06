"""Sistema de eventos: notificaciones con tipo/payload/status accionables."""

from datetime import date

from tacticore.core.calendar import GameCalendar
from tacticore.core.game import GameState
from tacticore.simulation import notifications as notif


def _game():
    return GameState(seed=1, calendar=GameCalendar(current_date=date(2026, 1, 5)))


def test_plain_notification_is_not_an_event():
    game = _game()
    n = notif.notify(game, "Hola", "info")
    assert n.kind == "" and n.status == "" and not n.is_pending_event


def test_event_starts_pending():
    game = _game()
    n = notif.notify(game, "Oferta", "msg", notif.FINANCE,
                     kind=notif.EVENT_SPONSOR_OFFER, payload={"x": 1})
    assert n.is_pending_event and n.status == "pending"
    assert notif.pending_events(game) == [n]


def test_mark_all_read_skips_pending_events():
    game = _game()
    info = notif.notify(game, "Info", "m")
    ev = notif.notify(game, "Ev", "m", kind=notif.EVENT_SPONSOR_OFFER, payload={})
    notif.mark_all_read(game)
    assert info.read is True
    assert ev.read is False and ev.is_pending_event   # sigue avisando
    assert notif.unread_count(game) == 1              # el evento pendiente


def test_resolve_closes_event():
    game = _game()
    ev = notif.notify(game, "Ev", "m", kind=notif.EVENT_SPONSOR_OFFER, payload={})
    notif.resolve(game, ev, "accepted")
    assert ev.status == "accepted" and ev.read is True
    assert not ev.is_pending_event and notif.pending_events(game) == []


def test_trim_never_drops_pending_events():
    game = _game()
    ev = notif.notify(game, "Ev", "m", kind=notif.EVENT_SPONSOR_OFFER, payload={})
    for i in range(notif._MAX + 50):     # desborda el tope con informativas
        notif.notify(game, f"n{i}", "m")
    assert ev in game.notifications                   # el pendiente sobrevive
    assert len(game.notifications) <= notif._MAX
