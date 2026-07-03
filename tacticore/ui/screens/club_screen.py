"""Seccion Club: la institucion.

Pestañas:
- Resumen: emblema + identidad del club (datos reales).
- Instalaciones: estadio y construcciones (placeholder).
- Empleados: staff, incluida la red de cazatalentos (placeholder).
- Aficionados: socios, animo de la hinchada y prensa (placeholder).
"""

from rich.text import Text

from ...simulation import facilities as fac
from ..format import append_section, hint, money
from ..identicon import emblem_lines
from .section_screen import SectionScreen

# Color de cada estado de un edificio (para la lista de instalaciones).
_FAC_STYLE = {
    "buildable": "green", "upgradable": "white", "maxed": "grey70",
    "in_progress": "yellow", "locked_tier": "grey50", "locked_req": "grey50",
    "coming_soon": "grey50",
}
_FAC_LEFT = 40  # ancho de la columna izquierda (lista) en Instalaciones
_FAC_RIGHT = 38  # ancho de la columna derecha (detalle): 80 - _FAC_LEFT - "| "


def _wrap(text: str, width: int) -> list[str]:
    """Parte `text` en lineas de a lo sumo `width` (corta por palabras)."""
    lines: list[str] = []
    cur = ""
    for word in text.split():
        if cur and len(cur) + 1 + len(word) > width:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    if cur:
        lines.append(cur)
    return lines or [""]


class ClubScreen(SectionScreen):
    """Datos de la institucion (identidad, instalaciones, staff, hinchada)."""

    section_key = "C"
    section_title = "Club"
    tabs = ("Resumen", "Instalaciones", "Empleados", "Aficionados")
    _FAC_TAB = 1  # indice de la pestana Instalaciones (la interactiva)

    def __init__(self) -> None:
        super().__init__()
        self._fac_sel = 0  # item seleccionado en Instalaciones

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

    # --- Instalaciones (interactiva: construir/mejorar edificios y gradas) ---
    def _fac_items(self) -> list:
        """Lista ordenada de items navegables: edificios del catalogo + gradas."""
        items = [("facility", s.id) for s in fac.CATALOG]
        items += [("stand", sec) for sec in fac.STANDS]
        return items

    def _facilities_text(self) -> Text:
        club = self._club
        if club is None:
            return Text("Sin club todavia.", style="white")
        items = self._fac_items()
        self._fac_sel = max(0, min(len(items) - 1, self._fac_sel))
        t = Text()
        t.append("INSTALACIONES   ", style="bold green")
        t.append(f"Parcelas {fac.plots_free(club)}/{club.plots}    ", style="white")
        t.append(f"Ingreso {money(fac.facility_income(club))}/sem\n", style="grey70")
        t.append("-" * 80 + "\n", style="grey50")
        left = self._fac_left_lines(club, items)
        right = self._fac_detail_lines(club, items)
        for i in range(max(len(left), len(right))):
            lline = left[i] if i < len(left) else Text("")
            rline = right[i] if i < len(right) else Text("")
            t.append_text(lline)
            t.append(" " * (_FAC_LEFT - len(lline.plain)))  # completa a _FAC_LEFT exacto
            t.append("| ", style="grey50")
            t.append_text(rline)
            t.append("\n")
        t.append_text(hint(("^v", "mover"), ("Enter", "construir/mejorar"),
                           ("+", "comprar parcela")))
        return t

    def _fac_left_lines(self, club, items) -> list:
        lines = [Text("EDIFICIOS", style="bold green")]
        for idx, (kind, key) in enumerate(items):
            if kind == "facility":
                lines.append(self._fac_row(club, idx, kind, key))
        lines.append(Text("ESTADIO (gradas)", style="bold green"))
        for idx, (kind, key) in enumerate(items):
            if kind == "stand":
                lines.append(self._fac_row(club, idx, kind, key))
        return lines

    def _fac_row(self, club, idx, kind, key) -> Text:
        if kind == "facility":
            s = fac.spec(key)
            lv = fac.level(club, key)
            status = fac.facility_status(club, key)
            tag = {
                "buildable": "-", "upgradable": f"Nv{lv}", "maxed": f"Nv{lv} MAX",
                "in_progress": "(obra)", "locked_tier": f"(Liga {s.min_tier.value})",
                "locked_req": "(requisito)", "coming_soon": "proximo",
            }[status]
            style = _FAC_STYLE[status]
            text = f" {s.name:<24}{tag}"
        else:
            seats, _cost, _days, mt = fac.STANDS[key]
            status = fac.stand_status(club, key)
            tag = {"buildable": f"+{seats}", "in_progress": "(obra)",
                   "locked_tier": f"(Liga {mt.value})"}[status]
            style = {"buildable": "green", "in_progress": "yellow",
                     "locked_tier": "grey50"}[status]
            text = f" {fac.stand_label(key):<24}{tag}"
        if idx == self._fac_sel:
            return Text(text.ljust(_FAC_LEFT), style="bold black on green")
        return Text(text[:_FAC_LEFT], style=style)

    def _fac_detail_lines(self, club, items) -> list:
        kind, key = items[self._fac_sel]
        lines = [Text("DETALLE", style="bold green")]
        if kind == "facility":
            lines += self._fac_detail_facility(club, key)
        else:
            lines += self._fac_detail_stand(club, key)
        lines.append(Text(""))
        lines.append(Text("Obras en curso:", style="bold green"))
        if club.constructions:
            for c in club.constructions:
                name = fac.spec(c.key).name if c.kind == "facility" else fac.stand_label(c.key)
                lines.append(Text(f"  {name} ({c.days_remaining}d)", style="yellow"))
        else:
            lines.append(Text("  ninguna", style="grey62"))
        return lines

    def _fac_detail_facility(self, club, key) -> list:
        s = fac.spec(key)
        lv = fac.level(club, key)
        status = fac.facility_status(club, key)
        lines = [
            Text(f"{s.name}  ({s.category})", style="bold white"),
            Text(f"Nivel {lv}/{s.max_level}", style="white"),
        ]
        if not s.buildable:
            lines.append(Text("Proximamente", style="grey62"))
            for wl in _wrap(s.future_note, _FAC_RIGHT - 2):
                lines.append(Text(f"  {wl}", style="grey62"))
            return lines
        eff = []
        if s.weekly_income:
            eff.append(f"+{money(s.weekly_income)}/sem")
        if s.popularity:
            eff.append(f"+{s.popularity:.2f} pop")
        lines.append(Text("Efecto x nivel: " + (", ".join(eff) if eff else "-"),
                          style="grey70"))
        if status in ("buildable", "upgradable"):
            target = lv + 1
            cost = fac.build_cost(s, target)
            needs_plot = lv == 0
            afford = club.capital >= cost and (not needs_plot or fac.plots_free(club) >= s.plots)
            verb = "Construir" if lv == 0 else f"Mejorar a Nv{target}"
            extra = f", {s.plots} parcela" if needs_plot else ""
            lines.append(Text(f"{verb}: {money(cost)} ({s.build_days}d{extra})",
                              style="green" if afford else "red"))
            lines.append(Text("[Enter] confirmar", style="grey62"))
        elif status == "locked_tier":
            lines.append(Text(f"Necesita liga {s.min_tier.value} o mejor", style="grey62"))
        elif status == "locked_req":
            reqs = ", ".join(f"{fac.spec(rid).name} Nv{rl}" for rid, rl in s.requires)
            lines.append(Text(f"Requiere: {reqs}", style="grey62"))
        elif status == "maxed":
            lines.append(Text("Al maximo nivel", style="grey62"))
        elif status == "in_progress":
            lines.append(Text("En obra", style="yellow"))
        return lines

    def _fac_detail_stand(self, club, key) -> list:
        seats, cost, days, mt = fac.STANDS[key]
        status = fac.stand_status(club, key)
        lines = [Text(f"{fac.stand_label(key)}  (+{seats} asientos)", style="bold white")]
        if status == "buildable":
            afford = club.capital >= cost and fac.plots_free(club) >= 1
            lines.append(Text(f"Construir: {money(cost)} ({days}d, 1 parcela)",
                              style="green" if afford else "red"))
            lines.append(Text("[Enter] confirmar", style="grey62"))
        elif status == "locked_tier":
            lines.append(Text(f"Necesita liga {mt.value} o mejor", style="grey62"))
        else:
            lines.append(Text("Ya hay una obra de esta grada", style="yellow"))
        return lines

    # --- Teclado (solo en la pestana Instalaciones) ---
    def on_content_key(self, event) -> None:
        if self._active_tab != self._FAC_TAB or self._club is None:
            return
        key = event.key
        items = self._fac_items()
        if key == "up":
            event.stop(); self._fac_sel = max(0, self._fac_sel - 1); self._refresh_content()
        elif key == "down":
            event.stop(); self._fac_sel = min(len(items) - 1, self._fac_sel + 1); self._refresh_content()
        elif key == "enter":
            event.stop()
            kind, k = items[self._fac_sel]
            if kind == "facility":
                fac.start_facility(self._club, k)
            else:
                fac.start_stand(self._club, k)
            self._refresh_content()
        elif event.character == "+":
            event.stop(); fac.buy_plot(self._club); self._refresh_content()

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
