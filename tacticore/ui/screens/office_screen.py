"""Seccion Oficina: el dashboard "de un pantallazo".

Pestañas:
- Resumen: proximo partido, posicion en la liga y estado del club (datos reales).
- Noticias: feed de novedades (aun sin sistema; estado vacio prolijo).
- Semana: el ciclo semanal del juego (entreno, finanzas, partido) por jornada.
"""

from rich.text import Text

from ...simulation.season import compute_standings
from ..format import append_section, money
from .section_screen import SectionScreen


class OfficeScreen(SectionScreen):
    """Dashboard inicial del manager."""

    section_key = "O"
    section_title = "Oficina"
    tabs = ("Resumen", "Noticias", "Semana")

    # --- Datos ---
    @property
    def _game(self):
        return self.app.game

    def _next_match(self):
        game = self._game
        league = game.player_league if game else None
        club = game.player_club if game else None
        if league is None or club is None:
            return None
        for m in sorted(league.matches, key=lambda m: m.matchday):
            if not m.played and (m.home is club or m.away is club):
                return m
        return None

    def _position(self):
        game = self._game
        league = game.player_league if game else None
        club = game.player_club if game else None
        if league is None or club is None:
            return None
        for pos, standing in enumerate(compute_standings(league), start=1):
            if standing.club is club:
                return pos, standing.points, len(league.clubs)
        return None

    # --- Render por pestaña ---
    def render_tab(self, index: int) -> Text:
        if index == 1:
            return self._news_text()
        if index == 2:
            return self._week_text()
        return self._summary_text()

    def _summary_text(self) -> Text:
        game = self._game
        club = game.player_club if game else None
        if club is None:
            return Text("Sin club todavia.", style="white")

        t = Text()
        # Proximo partido.
        m = self._next_match()
        if m is None:
            match_rows = [("No hay proximos partidos.", "grey62")]
        else:
            rival = m.away if m.home is club else m.home
            sede = "Local" if m.home is club else "Visitante"
            match_rows = [
                (f"Jornada {m.matchday}  -  {m.kind.value}", "bold white"),
                f"{club.name}  vs  {rival.name}",
                (f"Condicion: {sede}", "grey62"),
            ]
        append_section(t, "PROXIMO PARTIDO", match_rows)

        # Liga + club, en una linea de dos columnas para aprovechar el ancho.
        pos = self._position()
        pos_txt = f"{pos[0]}o de {pos[2]}   ({pos[1]} pts)" if pos else "-"
        append_section(t, "SITUACION", [
            f"Posicion en la liga: {pos_txt}",
            f"Caja: {money(club.capital):<18} Socios: {club.members}",
        ])

        # Novedades (placeholder).
        append_section(t, "ULTIMAS NOVEDADES", [
            ("(sin novedades por ahora)", "grey62"),
        ])
        return t

    def _news_text(self) -> Text:
        t = Text()
        append_section(t, "NOTICIAS", [
            ("Todavia no hay noticias.", "grey62"),
            ("Aca vas a ver resultados, fichajes, lesiones, nuevos socios,", "grey62"),
            ("el animo de la hinchada y la prensa del club.", "grey62"),
        ])
        return t

    def _week_text(self) -> Text:
        # "La semana": placeholder del ciclo con dias fijos. Todavia sin fechas
        # reales (los partidos van por jornada, no por dia). Ver nota en el plan.
        t = Text()
        append_section(t, "LA SEMANA", [
            ("El ciclo semanal (entreno, finanzas, partido) va a vivir aca.", "grey62"),
            "",
            ("Lun  Entrenamiento", "grey70"),
            ("Mie  Actualizacion financiera", "grey70"),
            ("Sab  Partido de liga", "grey70"),
            "",
            ("Proximamente: fechas reales de calendario por jornada.", "grey62"),
        ])
        return t
