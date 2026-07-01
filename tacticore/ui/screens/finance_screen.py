"""Seccion Finanzas: la economia del club.

Pestañas:
- Balance: caja actual y masa salarial semanal (datos reales).
- Sueldos: el sueldo de cada jugador (calculado por atributos/edad).
- Patrocinadores: sponsors e ingresos (placeholder).
- Movimientos: registro de ingresos/gastos (placeholder).
"""

from rich.text import Text

from ...simulation.economy import player_salary, squad_wage_bill
from ..format import append_section, money
from .section_screen import SectionScreen


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
        t = Text()
        append_section(t, "BALANCE", [
            (f"Caja actual:            {money(club.capital)}", "bold white"),
            "",
            (f"Masa salarial semanal:  -{money(wages)}", "red"),
            (f"Ingresos de la semana:   {money(0)}   (proximamente)", "grey62"),
            "-" * 40,
            (f"Resultado semanal:      -{money(wages)}", "red"),
        ])
        t.append("\n")
        t.append("Los ingresos (entradas, patrocinadores, premios) llegan con\n",
                 style="grey62")
        t.append("el ciclo semanal y el mercado.", style="grey62")
        return t

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
        t = Text()
        append_section(t, "PATROCINADORES", [
            ("Todavia no hay patrocinadores.", "grey62"),
            "",
            ("Proximamente vas a poder negociar sponsors (camiseta, estadio)", "grey62"),
            ("que daran ingresos periodicos segun tu rendimiento y categoria.", "grey62"),
        ])
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
