"""Seccion Club: la institucion.

Pestañas:
- Resumen: emblema + identidad del club (datos reales).
- Instalaciones: estadio y construcciones (placeholder).
- Empleados: staff, incluida la red de cazatalentos (placeholder).
- Aficionados: socios, animo de la hinchada y prensa (placeholder).
"""

from rich.text import Text

from ...simulation.economy import TICKET_PRICES, stadium_upkeep
from ..format import append_section, money
from ..identicon import emblem_lines
from .section_screen import SectionScreen


class ClubScreen(SectionScreen):
    """Datos de la institucion (identidad, instalaciones, staff, hinchada)."""

    section_key = "C"
    section_title = "Club"
    tabs = ("Resumen", "Instalaciones", "Empleados", "Aficionados")

    @property
    def _club(self):
        game = self.app.game
        return game.player_club if game else None

    def render_tab(self, index: int) -> Text:
        if index == 1:
            return self._facilities_text()
        if index == 2:
            return self._staff_text()
        if index == 3:
            return self._fans_text()
        return self._summary_text()

    def _summary_text(self) -> Text:
        club = self._club
        if club is None:
            return Text("Sin club todavia.", style="white")

        manager = club.manager.full_name if club.manager else "-"
        info = [
            "",
            (f"{club.name}  ({club.short_name})", "bold white"),
            (f"Liga {club.tier.value}   Pais: {club.country_code}", "grey62"),
            f"Manager: {manager}",
            f"Socios: {club.members}",
            f"Capital: {money(club.capital)}",
            (f"OVR plantel: {club.overall}", "grey70"),
        ]
        # El emblema (7 filas) al costado de la identidad, componiendo cada fila.
        t = Text()
        rows = emblem_lines(club.name)
        for i, emblem_row in enumerate(rows):
            t.append_text(emblem_row)
            t.append("   ")
            text, style = info[i] if isinstance(info[i], tuple) else (info[i], "white")
            t.append(text, style=style)
            t.append("\n")
        t.append("\n")
        append_section(t, "ESTADIO E HINCHADA", [
            f"Estadio: {club.stadium.name}  (cap. {club.stadium.capacity:,})".replace(",", "."),
            f"Hinchada: {club.fans_name}",
        ])
        return t

    _SECTORS = (("General", "general"), ("Preferente", "preferente"),
                ("Tribuna", "tribuna"), ("Palco", "palco"))

    def _facilities_text(self) -> Text:
        club = self._club
        if club is None:
            return Text("Sin club todavia.", style="white")
        st = club.stadium
        cap = f"{st.capacity:,}".replace(",", ".")
        t = Text()
        t.append("ESTADIO\n", style="bold green")
        t.append(f"  {st.name}    Capacidad: {cap}\n\n", style="white")
        t.append(f"  {'SECTOR':<12}{'ASIENTOS':>10}{'ENTRADA':>10}\n", style="bold green")
        t.append("  " + "-" * 32 + "\n", style="grey50")
        for label, attr in self._SECTORS:
            seats = f"{getattr(st, attr):,}".replace(",", ".")
            t.append(f"  {label:<12}{seats:>10}{money(TICKET_PRICES[attr]):>10}\n",
                     style="white")
        t.append(f"\n  Mantenimiento semanal: {money(stadium_upkeep(st.capacity))}\n\n",
                 style="grey70")
        append_section(t, "CONSTRUCCION", [
            ("Proximamente vas a poder ampliar sectores y construir edificios", "grey62"),
            ("(tienda, museo, centro de entrenamiento...) comprando parcelas.", "grey62"),
        ])
        return t

    def _staff_text(self) -> Text:
        club = self._club
        t = Text()
        coach = club.coach if club else None
        if coach is None:
            append_section(t, "DIRECTOR TECNICO",
                           [("Sin director tecnico.", "grey62")])
        else:
            today = self.app.game.calendar.current_date
            rows = [
                (f"{'Nombre':<12}{coach.full_name}", "bold white"),
                (f"{'Nacion.':<12}{coach.nationality}    Edad: {coach.age_on(today)}",
                 "white"),
                (f"{'Mentalidad':<12}{coach.mentality.value}", "white"),
                (f"{'Habilidad':<12}{coach.skill:.1f}   (calidad del entreno)", "grey70"),
                (f"{'Liderazgo':<12}{coach.leadership:.1f}   (influye en la moral)",
                 "grey70"),
            ]
            append_section(t, "DIRECTOR TECNICO", rows)
        # Resto del cuerpo de trabajo (placeholder).
        append_section(t, "OTRO PERSONAL", [
            ("El resto del cuerpo de trabajo vivira aca.", "grey62"),
            "",
            ("  - Entrenadores asistentes", "grey70"),
            ("  - Medicos y preparadores fisicos", "grey70"),
            ("  - Red de cazatalentos (ojeadores de la cantera)", "grey70"),
            "",
            ("Los cazatalentos alimentaran la Cantera (en Jugadores).", "grey62"),
        ])
        return t

    def _fans_text(self) -> Text:
        club = self._club
        t = Text()
        append_section(t, "AFICIONADOS", [
            (f"Socios: {club.members if club else '-'}", "white"),
            (f"Hinchada: {club.fans_name if club else '-'}", "white"),
            "",
            ("Proximamente: animo de la hinchada, altas y bajas de socios,", "grey62"),
            ("expectativas y prensa del club (mas roleplay).", "grey62"),
        ])
        return t
