"""Modal de una oferta de patrocinio (evento accionable).

Se abre desde Club > Notificaciones con Enter sobre una oferta pendiente. Muestra
los terminos y deja ACEPTAR (firma el contrato, entra el bono de firma) o RECHAZAR
(el cupo sigue libre y llegara otra oferta). Esc vuelve sin decidir (la oferta sigue
pendiente hasta que caduque).
"""

from datetime import date

from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Static

from ...persistence import savegame
from ...simulation import sponsors as sp
from ..format import hint, money
from .base_screen import BaseScreen

_W = 64


class SponsorOfferScreen(BaseScreen):
    """Ver una oferta de patrocinio y aceptar/rechazar."""

    BINDINGS = [
        ("escape", "cancel", "Volver"),
        ("enter", "accept", "Aceptar"),
        ("r", "reject", "Rechazar"),
    ]

    CSS = """
    #viewport { align: center top; }
    #card { width: 66; height: auto; margin-top: 2; }
    #hint { width: 66; text-align: center; color: $text-muted; margin-top: 1; }
    """

    def __init__(self, game, notification, on_close=None) -> None:
        super().__init__()
        self._game = game
        self._n = notification
        self._on_close = on_close

    def compose_viewport(self) -> ComposeResult:
        yield Static(self._card_text(), id="card")
        yield Static(
            hint(("Enter", "aceptar"), ("R", "rechazar"), ("Esc", "volver"), sep="  "),
            id="hint",
        )

    def _card_text(self) -> Text:
        p = self._n.payload
        club = self._game.player_club
        used, slots = len(sp.active_sponsors(club)), sp.slots_for_tier(club.tier)
        expires = date.fromisoformat(p["expires"])
        t = Text()
        t.append("OFERTA DE PATROCINIO\n", style="bold green")
        t.append("-" * _W + "\n", style="grey50")
        t.append(f"{'Marca':<14}", style="grey62")
        t.append(f"{p['name']}  ({p['sector']})\n", style="bold white")
        t.append(f"{'Calidad marca':<14}{'*' * p['tier']}{'-' * (5 - p['tier'])}\n", style="white")
        t.append(f"{'Pago semanal':<14}", style="grey62")
        t.append(f"{money(p['weekly_pay'])}/sem\n", style="green")
        t.append(f"{'Duracion':<14}{p['weeks_total']} semanas\n", style="white")
        if p["signing_bonus"]:
            t.append(f"{'Bono de firma':<14}{money(p['signing_bonus'])}\n", style="white")
        if p["promotion_bonus"]:
            t.append(f"{'Bono ascenso':<14}{money(p['promotion_bonus'])}\n", style="grey70")
        if p["streak_bonus"]:
            t.append(f"{'Bono racha':<14}{money(p['streak_bonus'])}  "
                     f"(cada {p['streak_len']} victorias)\n", style="grey70")
        t.append(f"{'Vence':<14}{expires.strftime('%d-%m-%Y')}\n", style="grey70")
        t.append("-" * _W + "\n", style="grey50")
        t.append(f"Cupos de patrocinador: {used}/{slots}\n", style="grey62")
        return t

    def _close(self) -> None:
        savegame.save_game(self._game)
        if self._on_close is not None:
            self._on_close()
        self.app.pop_screen()

    def action_accept(self) -> None:
        sp.accept_offer(self._game, self._n)
        self._close()

    def action_reject(self) -> None:
        sp.reject_offer(self._game, self._n)
        self._close()

    def action_cancel(self) -> None:
        self.app.pop_screen()  # queda pendiente