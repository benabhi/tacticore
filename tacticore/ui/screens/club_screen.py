"""Seccion Club: la institucion.

Pestañas:
- Resumen: emblema + identidad del club (datos reales).
- Instalaciones: estadio y construcciones (placeholder).
- Empleados: staff, incluida la red de cazatalentos (placeholder).
- Aficionados: socios, animo de la hinchada y prensa (placeholder).
"""

from rich.text import Text

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

    def _facilities_text(self) -> Text:
        club = self._club
        t = Text()
        cap = f"{club.stadium.capacity:,}".replace(",", ".") if club else "-"
        append_section(t, "INSTALACIONES", [
            (f"Estadio: {club.stadium.name if club else '-'}  (cap. {cap})", "white"),
            "",
            ("Proximamente vas a poder construir y mejorar:", "grey62"),
            ("  - Ampliaciones del estadio", "grey70"),
            ("  - Centro de entrenamiento", "grey70"),
            ("  - Complejo juvenil (para la cantera)", "grey70"),
            ("Cada construccion tendra un costo y dara beneficios.", "grey62"),
        ])
        return t

    def _staff_text(self) -> Text:
        t = Text()
        append_section(t, "EMPLEADOS", [
            ("El cuerpo de trabajo del club vivira aca.", "grey62"),
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
