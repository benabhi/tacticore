"""Seccion Finanzas: la economia del club.

Pestañas:
- Balance: el flujo semanal RECURRENTE completo (socios, patrocinadores, instalaciones y
  el bonus de gestion del staff vs sueldos de jugadores, empleados y mantenimiento) mas
  indicadores (caja, valor del plantel, patrimonio, taquilla promedio). No proyecta la
  taquilla: entra cuando se juega de local (ver Movimientos).
- Patrocinadores: los contratos activos con su detalle y los cupos libres.
- Movimientos: el libro de caja real (ingresos y gastos a medida que ocurren), paginado.
"""

from rich.text import Text

from ...simulation import staff
from ...simulation.economy import (
    membership_income, player_value, squad_wage_bill, stadium_upkeep)
from ...simulation.facilities import facility_income
from ...simulation.finance_log import newest_first
from ..format import hint, money
from .section_screen import SectionScreen

_COL = 36   # ancho de cada columna (etiqueta + monto) del flujo semanal
_LBL = 24   # ancho de la etiqueta dentro de la columna (el resto va al monto)
_MOV_PAGE = 15  # movimientos por pagina


class FinanceScreen(SectionScreen):
    """Balance, patrocinadores y movimientos del club."""

    section_key = "F"
    section_title = "Finanzas"
    tabs = ("Balance", "Patrocinadores", "Movimientos")
    _MOV_TAB = 2

    def __init__(self) -> None:
        super().__init__()
        self._mov_page = 0

    @property
    def _club(self):
        game = self.app.game
        return game.player_club if game else None

    @property
    def _today(self):
        return self.app.game.calendar.current_date

    def render_tab(self, index: int) -> Text:
        if index == 1:
            return self._sponsors_text()
        if index == 2:
            return self._movements_text()
        return self._balance_text()

    # --- Balance ---
    def _weekly(self, club):
        """Rubros del cierre semanal (igual que daily._weekly_economy)."""
        dues = membership_income(club.members)
        facs = facility_income(club)
        sponsor = sum(s.weekly_pay for s in club.sponsors if s.active)
        gestion = round((dues + facs) * staff.income_bonus(club))
        wages = round(squad_wage_bill(club.players, self._today) * (1 - staff.wage_reduction(club)))
        staff_wages = staff.staff_wage_bill(club)
        upkeep = stadium_upkeep(club.stadium.capacity)
        incomes = [("Cuota de socios", dues), ("Patrocinadores", sponsor),
                   ("Instalaciones", facs)]
        if gestion:
            incomes.append(("Gestion (staff)", gestion))
        expenses = [("Sueldos jugadores", wages), ("Empleados", staff_wages),
                    ("Mantenimiento", upkeep)]
        return incomes, expenses

    def _balance_text(self) -> Text:
        club = self._club
        if club is None:
            return Text("Sin club todavia.", style="white")
        incomes, expenses = self._weekly(club)
        total_in = sum(v for _, v in incomes)
        total_out = sum(v for _, v in expenses)
        net = total_in - total_out

        t = Text()
        t.append("FLUJO SEMANAL RECURRENTE  ", style="bold green")
        t.append("(se cobra/paga los viernes)\n\n", style="grey62")
        self._two(t, "INGRESOS", "GASTOS", "bold green")
        t.append("  " + "-" * _COL + "  " + "-" * _COL + "\n", style="grey50")
        for i in range(max(len(incomes), len(expenses))):
            self._two_pair(t, incomes[i] if i < len(incomes) else None,
                           expenses[i] if i < len(expenses) else None)
        t.append("  " + "-" * _COL + "  " + "-" * _COL + "\n", style="grey50")
        self._two_pair(t, ("Total ingresos", total_in), ("Total gastos", total_out),
                       style="bold white")
        t.append("\n")
        sign = "+" if net >= 0 else "-"
        t.append("  Resultado semanal recurrente:  ")
        t.append(f"{sign}{money(abs(net))}\n\n", style="bold green" if net >= 0 else "bold red")

        # Indicadores (caja, plantel, patrimonio, taquilla promedio).
        squad_value = sum(player_value(p, self._today) for p in club.players)
        gates = [mv.amount for mv in club.movements if mv.concept.startswith("Taquilla")]
        gate_avg = round(sum(gates) / len(gates)) if gates else 0
        t.append("  " + "-" * (2 * _COL + 2) + "\n", style="grey50")
        self._two_pair(t, ("Caja actual", club.capital),
                       ("Valor del plantel", squad_value), style="white")
        self._two_pair(t, ("Patrimonio neto", club.capital + squad_value),
                       ("Taquilla prom. local", gate_avg), style="white")
        t.append("\n  La taquilla y los fichajes entran al ocurrir (ver Movimientos).",
                 style="grey50")
        return t

    def _two(self, t: Text, left: str, right: str, style: str) -> None:
        t.append("  ")
        t.append(left.ljust(_COL), style=style)
        t.append("  ")
        t.append(right, style=style)
        t.append("\n")

    def _two_pair(self, t: Text, left, right, style: str = "white") -> None:
        def cell(pair):
            if pair is None:
                return " " * _COL
            label, value = pair
            return f"{label[:_LBL]:<{_LBL}}{money(value):>{_COL - _LBL}}"
        t.append("  ")
        t.append(cell(left), style=style)
        t.append("  ")
        t.append(cell(right), style=style)
        t.append("\n")

    # --- Patrocinadores ---
    def _sponsors_text(self) -> Text:
        from ...simulation import sponsors as sp

        club = self._club
        t = Text()
        if club is None:
            return Text("Sin club todavia.", style="white")
        active = [s for s in club.sponsors if s.active]
        slots = sp.slots_for_tier(club.tier)
        total = sum(c.weekly_pay for c in active)
        t.append(f"PATROCINADORES  ", style="bold green")
        t.append(f"({len(active)}/{slots} cupos)   Total {money(total)}/sem\n", style="white")
        t.append("-" * 80 + "\n", style="grey50")
        t.append("  MARCA             SECTOR        CAL  PAGO/SEM    SEM    BONOS\n",
                 style="bold green")
        for c in active:
            s = c.sponsor
            stars = "*" * s.tier + "-" * (5 - s.tier)
            bonos = []
            if c.promotion_bonus:
                bonos.append(f"asc {money(c.promotion_bonus)}")
            if c.streak_bonus:
                bonos.append(f"racha {money(c.streak_bonus)}/{c.streak_len}v")
            t.append(f"  {s.name:<16.16}  {s.sector:<12.12}  {stars}  "
                     f"{money(c.weekly_pay):>8}  {c.weeks_remaining:>2}/{c.weeks_total:<2}  "
                     f"{', '.join(bonos)[:20]}\n", style="white")
        for _ in range(slots - len(active)):
            t.append("  (cupo libre: llegara una oferta en Notificaciones)\n", style="grey62")
        if not active and slots == 0:
            t.append("  Sin cupos de patrocinador en esta division.\n", style="grey62")
        t.append("\n  Las ofertas llegan como evento a Club > Notificaciones cuando se\n"
                 "  libera un cupo (al vencer un contrato o al ascender de division).",
                 style="grey50")
        return t

    # --- Movimientos (paginado) ---
    def _movements_text(self) -> Text:
        club = self._club
        if club is None:
            return Text("Sin club todavia.", style="white")
        movements = newest_first(club)
        t = Text()
        if not movements:
            t.append("MOVIMIENTOS\n", style="bold green")
            t.append("-" * 80 + "\n", style="grey50")
            t.append("  Todavia no hubo movimientos.\n", style="grey62")
            t.append("  Aca aparecen apenas ocurren: taquilla, sueldos, patrocinadores,\n"
                     "  empleados, obras y fichajes (compras y ventas).", style="grey62")
            return t
        ingresos = sum(mv.amount for mv in movements if mv.amount > 0)
        gastos = -sum(mv.amount for mv in movements if mv.amount < 0)
        pages = max(1, (len(movements) + _MOV_PAGE - 1) // _MOV_PAGE)
        self._mov_page = max(0, min(pages - 1, self._mov_page))
        rows = movements[self._mov_page * _MOV_PAGE: self._mov_page * _MOV_PAGE + _MOV_PAGE]

        t.append(f"MOVIMIENTOS ({len(movements)})   ", style="bold green")
        t.append(f"Ingresos {money(ingresos)}   ", style="green")
        t.append(f"Gastos {money(gastos)}", style="red")
        if pages > 1:
            t.append(f"   Pag {self._mov_page + 1}/{pages}", style="grey62")
        t.append("\n")
        t.append("-" * 80 + "\n", style="grey50")
        for mv in rows:
            when = mv.date.strftime("%d-%m-%Y")
            signed = ("+" if mv.amount >= 0 else "-") + money(abs(mv.amount))
            t.append(f"  {when}  ", style="grey50")
            t.append(f"{mv.concept:<48.48}", style="white")
            t.append(f"{signed:>14}\n", style="green" if mv.amount >= 0 else "red")
        if pages > 1:
            t.append("\n")
            t.append_text(hint(("izq/der", "pagina")))
        return t

    def on_content_key(self, event) -> None:
        if self._active_tab != self._MOV_TAB or self._club is None:
            return
        if event.key in ("left", "pageup"):
            event.stop(); self._mov_page = max(0, self._mov_page - 1); self._refresh_content()
        elif event.key in ("right", "pagedown"):
            event.stop(); self._mov_page += 1; self._refresh_content()
