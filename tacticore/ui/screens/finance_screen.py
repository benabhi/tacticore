"""Seccion Finanzas: la economia del club.

Pestañas:
- Balance: caja actual y masa salarial semanal (datos reales).
- Sueldos: el sueldo de cada jugador (calculado por atributos/edad).
- Patrocinadores: sponsors e ingresos (placeholder).
- Movimientos: registro de ingresos/gastos (placeholder).
"""

from rich.text import Text

from ...simulation.economy import (
    matchday_income,
    membership_income,
    player_salary,
    squad_wage_bill,
    stadium_upkeep,
)
from ..format import append_section, money
from .section_screen import SectionScreen

_COL = 30   # ancho de cada columna (etiqueta + monto) del resumen
_LBL = 21   # ancho de la etiqueta dentro de la columna (el resto va al monto)


class FinanceScreen(SectionScreen):
    """Balance, sueldos, patrocinadores y movimientos del club."""

    section_key = "F"
    section_title = "Finanzas"
    tabs = ("Balance", "Sueldos", "Patrocinadores", "Movimientos")

    @property
    def _club(self):
        game = self.app.game
        return game.player_club if game else None

    @property
    def _today(self):
        return self.app.game.calendar.current_date

    def _next_home_match(self):
        """Proximo partido de local del club (para estimar la taquilla), o None."""
        game = self.app.game
        league = game.player_league if game else None
        club = self._club
        if league is None or club is None:
            return None
        for m in sorted(league.matches, key=lambda m: m.matchday):
            if not m.played and m.home is club:
                return m
        return None

    def render_tab(self, index: int) -> Text:
        if index == 1:
            return self._salaries_text()
        if index == 2:
            return self._sponsors_text()
        if index == 3:
            return self._movements_text()
        return self._balance_text()

    def _balance_text(self) -> Text:
        club = self._club
        if club is None:
            return Text("Sin club todavia.", style="white")

        wages = squad_wage_bill(club.players, self._today)
        nxt = self._next_home_match()
        gate = matchday_income(club, nxt.away) if nxt is not None else 0
        sponsor = club.sponsor.weekly_pay if (club.sponsor and club.sponsor.active) else 0
        incomes = [
            ("Cuota de socios", membership_income(club.members)),
            ("Patrocinador", sponsor),
            ("Taquilla (prox local)", gate),
            ("Venta de jugadores", 0),
        ]
        expenses = [
            ("Sueldos", wages),
            ("Mantenimiento estadio", stadium_upkeep(club.stadium.capacity)),
            ("Empleados", 0),
            ("Otros", 0),
        ]
        total_in = sum(v for _, v in incomes)
        total_out = sum(v for _, v in expenses)
        net = total_in - total_out

        t = Text()
        t.append("Resumen semanal estimado\n\n", style="grey62")
        # Encabezados de las dos columnas.
        t.append("  ")
        t.append("INGRESOS".ljust(_COL), style="bold green")
        t.append("   ")
        t.append("GASTOS", style="bold green")
        t.append("\n")
        t.append("  " + "-" * _COL + "   " + "-" * _COL + "\n", style="grey50")
        for i in range(max(len(incomes), len(expenses))):
            li = incomes[i] if i < len(incomes) else None
            ri = expenses[i] if i < len(expenses) else None
            self._fin_row(t, li, ri)
        t.append("  " + "-" * _COL + "   " + "-" * _COL + "\n", style="grey50")
        self._fin_row(t, ("Total ingresos", total_in), ("Total gastos", total_out),
                      style="bold white")
        t.append("\n")

        # Resultado y proyeccion de caja.
        sign = "+" if net >= 0 else "-"
        res_style = "bold green" if net >= 0 else "bold red"
        t.append("  Resultado semanal estimado:  ")
        t.append(f"{sign}{money(abs(net))}\n", style=res_style)
        t.append("  Caja actual: ")
        t.append(money(club.capital), style="bold white")
        t.append("     Proyectada (fin de semana): ")
        t.append(money(club.capital + net) + "\n", style="bold white")
        return t

    def _fin_row(self, t: Text, left, right, style: str = "white") -> None:
        """Una fila del resumen: (etiqueta, monto) a la izquierda y a la derecha."""
        def cell(pair):
            if pair is None:
                return " " * _COL
            label, value = pair
            return f"{label[:_LBL]:<{_LBL}}{money(value):>{_COL - _LBL}}"
        t.append("  ")
        t.append(cell(left), style=style)
        t.append("   ")
        t.append(cell(right), style=style)
        t.append("\n")

    def _salaries_text(self) -> Text:
        club = self._club
        if club is None:
            return Text("Sin club todavia.", style="white")
        players = sorted(
            club.players, key=lambda p: player_salary(p, self._today), reverse=True
        )
        t = Text()
        total = squad_wage_bill(club.players, self._today)
        t.append(f"Sueldos semanales   (total: {money(total)})\n\n", style="grey62")
        t.append("  #   JUGADOR                       POS   SUELDO\n", style="bold green")
        t.append("-" * 52 + "\n", style="grey50")
        for p in players:
            salary = player_salary(p, self._today)
            t.append(f"  {str(p.shirt_number or '-'):>2}  ")
            t.append(f"{p.full_name:<28.28}  ")
            t.append(f"{p.position.value:<4}  ")
            t.append(f"{money(salary):>8}\n", style="white")
        return t

    def _sponsors_text(self) -> Text:
        club = self._club
        t = Text()
        contract = club.sponsor if club else None
        if contract is None:
            append_section(t, "PATROCINADOR", [("Sin patrocinador.", "grey62")])
            return t
        s = contract.sponsor
        rows = [
            (f"{'Marca':<14}{s.name}  ({s.sector})", "bold white"),
            (f"{'Tier':<14}{s.tier}", "white"),
            (f"{'Contrato':<14}{contract.weeks_remaining}/{contract.weeks_total} semanas restantes",
             "white"),
            (f"{'Pago semanal':<14}{money(contract.weekly_pay)}", "green"),
        ]
        if contract.promotion_bonus:
            rows.append((f"{'Bonus ascenso':<14}{money(contract.promotion_bonus)}", "grey70"))
        if contract.streak_bonus:
            rows.append(
                (f"{'Bonus racha':<14}{money(contract.streak_bonus)}  "
                 f"(cada {contract.streak_len} victorias)", "grey70"))
        append_section(t, "PATROCINADOR", rows)
        return t

    def _movements_text(self) -> Text:
        t = Text()
        append_section(t, "MOVIMIENTOS", [
            ("Sin movimientos registrados.", "grey62"),
            "",
            ("Aca se listaran ingresos y gastos: sueldos, fichajes,", "grey62"),
            ("entradas, premios y construcciones.", "grey62"),
        ])
        return t
