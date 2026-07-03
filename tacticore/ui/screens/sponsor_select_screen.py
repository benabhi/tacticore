"""Eleccion del patrocinador principal al fundar el club.

Se abre al final de "Crea tu club": muestra 3 ofertas de patrocinio con distinta
duracion, pago semanal y bonus. Se elige con las flechas y se firma con Enter. La
oferta elegida vuelve por callback (la pantalla que la abrio setea el contrato y
acredita el bono de firma).
"""

from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Static

from ..format import hint, money
from .base_screen import BaseScreen

_W = 72


class SponsorSelectScreen(BaseScreen):
    """Elegi 1 de 3 ofertas de patrocinio (flechas + Enter)."""

    BINDINGS = [
        ("up", "move(-1)", "Arriba"),
        ("down", "move(1)", "Abajo"),
        ("enter", "choose", "Firmar"),
    ]

    CSS = """
    #viewport { align: center top; }
    #sp_title { width: 1fr; text-align: center; color: green; text-style: bold; padding: 1 0 0 0; }
    #sp_sub { width: 1fr; text-align: center; color: $text-muted; }
    #sp_card { width: 72; height: auto; margin-top: 1; }
    #sp_hint { width: 72; text-align: center; color: $text-muted; margin-top: 1; }
    """

    def __init__(self, offers: list, on_pick) -> None:
        super().__init__()
        self._offers = offers
        self._on_pick = on_pick
        self._sel = 0

    def compose_viewport(self) -> ComposeResult:
        yield Static("ELEGI UN PATROCINADOR", id="sp_title")
        yield Static("Firmas por un tiempo: el que mas paga no siempre es el mejor.",
                     id="sp_sub")
        yield Static(self._card_text(), id="sp_card")
        yield Static(hint(("Flechas", "elegir"), ("Enter", "firmar")), id="sp_hint")

    def _refresh(self) -> None:
        self.query_one("#sp_card", Static).update(self._card_text())

    def _card_text(self) -> Text:
        t = Text()
        for i, c in enumerate(self._offers):
            selected = i == self._sel
            s = c.sponsor
            head = f"{s.name} ({s.sector})   Tier {s.tier}"
            l1 = f"Duracion: {c.weeks_total} semanas    Pago: {money(c.weekly_pay)}/sem"
            l2 = f"Firma: {money(c.signing_bonus)}"
            bonuses = []
            if c.promotion_bonus:
                bonuses.append(f"Ascenso: {money(c.promotion_bonus)}")
            if c.streak_bonus:
                bonuses.append(f"Racha x{c.streak_len}: {money(c.streak_bonus)}")
            l2 += "    " + ("   ".join(bonuses) if bonuses else "sin bonus extra")
            if selected:
                t.append(("> " + head).ljust(_W) + "\n", style="bold black on green")
                t.append(("  " + l1).ljust(_W) + "\n", style="black on green")
                t.append(("  " + l2).ljust(_W) + "\n", style="black on green")
            else:
                t.append("  " + head + "\n", style="bold white")
                t.append("  " + l1 + "\n", style="grey70")
                t.append("  " + l2 + "\n", style="grey62")
            t.append("\n")
        return t

    def action_move(self, delta: int) -> None:
        self._sel = max(0, min(len(self._offers) - 1, self._sel + delta))
        self._refresh()

    def action_choose(self) -> None:
        if self._offers:
            self._on_pick(self._offers[self._sel])
