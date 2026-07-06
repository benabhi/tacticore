"""Seccion Club: la institucion.

Pestañas:
- Resumen: emblema + identidad del club (datos reales).
- Instalaciones: estadio y construcciones (placeholder).
- Empleados: staff, incluida la red de cazatalentos (placeholder).
- Aficionados: socios, animo de la hinchada y prensa (placeholder).
"""

from rich.text import Text

from ...core.rng import new_rng
from ...domain.enums import EmployeeRole
from ...generators.employee_generator import EmployeeGenerator
from ...persistence import savegame
from ...simulation import facilities as fac
from ...simulation import staff
from ..format import append_section, hint, money
from ..identicon import emblem_lines
from .section_screen import SectionScreen

# Titulo de la seccion de cada rol de empleado en la pestana Empleados.
_ROLE_SECTION = {
    EmployeeRole.DOCTOR: "CUERPO MEDICO",
    EmployeeRole.FINANCE: "DIRECCION FINANCIERA",
}
# Alto fijo del bloque de dos columnas de Empleados: empuja la ayuda al fondo del
# area de contenido, dejando una linea en blanco antes del menu inferior (el total
# queda en 19 lineas: cabecera + regla + _STAFF_ROWS + ayuda).
_STAFF_ROWS = 16

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
    _FAC_TAB = 1    # indice de la pestana Instalaciones (interactiva)
    _STAFF_TAB = 2  # indice de la pestana Empleados (interactiva)

    def __init__(self) -> None:
        super().__init__()
        self._fac_sel = 0  # item seleccionado en Instalaciones
        self._emp_sel = 0  # empleado seleccionado en Empleados

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
        t.append(f"Parcela: {money(fac.plot_cost(club))}    ", style="grey70")
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

    # --- Teclado (pestanas interactivas: Instalaciones y Empleados) ---
    def on_content_key(self, event) -> None:
        if self._club is None:
            return
        if self._active_tab == self._FAC_TAB:
            self._facilities_key(event)
        elif self._active_tab == self._STAFF_TAB:
            self._staff_key(event)

    def _facilities_key(self, event) -> None:
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

    def _staff_key(self, event) -> None:
        # OJO: el frame se queda con las letras de seccion (o/c/j/p/e/f) antes de
        # llegar aca, por eso "contratar" va en Enter (no en 'c') y "despedir" en
        # Supr/Retroceso/'d'.
        key = event.key
        items = self._emp_items()
        if key == "up":
            event.stop(); self._emp_sel = max(0, self._emp_sel - 1); self._refresh_content()
        elif key == "down":
            event.stop(); self._emp_sel = min(len(items) - 1, self._emp_sel + 1); self._refresh_content()
        elif key == "enter":
            event.stop()
            if items:
                kind, _role, e = items[self._emp_sel]
                if kind == "cand" and staff.hire(self.app.game, e):
                    savegame.save_game(self.app.game)
                    self._refresh_content()
        elif key in ("delete", "backspace") or event.character in ("d", "D"):
            event.stop()
            if items:
                kind, _role, e = items[self._emp_sel]
                if kind == "staff":
                    staff.fire(self.app.game, e)
                    self._emp_sel = max(0, self._emp_sel - 1)
                    savegame.save_game(self.app.game)
                    self._refresh_content()

    def _candidates(self, role) -> list:
        """Terna de candidatos del rol para HOY (determinista; vacia si no hay cupo).

        Se regenera en cada render con la misma semilla (seed + fecha + rol): el
        "mercado" de empleados es estable en el dia y rota con el calendario."""
        club = self._club
        if not staff.can_hire(club, role):
            return []
        today = self.app.game.calendar.current_date
        offset = 100 * (list(EmployeeRole).index(role) + 1)
        gen = EmployeeGenerator(new_rng(self.app.game.seed + today.toordinal() + offset))
        return gen.candidates(role, club.tier, club.country_code, today, n=3)

    def _emp_items(self) -> list:
        """Items navegables de Empleados, en orden de rol: staff (despedible) y
        candidatos (contratable). Cada item es (kind, role, employee)."""
        club = self._club
        if club is None:
            return []
        out = []
        for role in EmployeeRole:
            out += [("staff", role, e) for e in staff.employees_of(club, role)]
            out += [("cand", role, e) for e in self._candidates(role)]
        return out

    def _staff_text(self) -> Text:
        club = self._club
        if club is None:
            return Text("Sin club todavia.", style="white")
        today = self.app.game.calendar.current_date
        items = self._emp_items()
        self._emp_sel = max(0, min(len(items) - 1, self._emp_sel)) if items else 0

        t = Text()
        coach = club.coach
        t.append("EMPLEADOS   ", style="bold green")
        if coach is not None:
            t.append(f"DT {coach.full_name} "
                     f"(Hab {coach.skill:.0f}, Lid {coach.leadership:.0f})   ",
                     style="white")
        t.append(f"Sueldos {money(staff.staff_wage_bill(club))}/sem\n", style="grey70")
        t.append("-" * 80 + "\n", style="grey50")

        left = self._emp_left_lines(club, today, items)
        right = self._emp_detail_lines(club, today, items)
        for i in range(_STAFF_ROWS):
            lline = left[i] if i < len(left) else Text("")
            rline = right[i] if i < len(right) else Text("")
            t.append_text(lline)
            t.append(" " * max(0, _FAC_LEFT - len(lline.plain)))
            t.append("| ", style="grey50")
            t.append_text(rline)
            t.append("\n")
        t.append_text(hint(("^v", "mover"), ("Enter", "contratar"),
                           ("Supr", "despedir")))
        return t

    def _emp_left_lines(self, club, today, items) -> list:
        """Columna izquierda: por rol, encabezado (no seleccionable) + sus filas."""
        lines = []
        idx = 0
        for role in EmployeeRole:
            emps = staff.employees_of(club, role)
            slots = staff.staff_slots(role, club.tier)
            lines.append(Text(f"{_ROLE_SECTION[role]} ({len(emps)}/{slots})",
                              style="bold green"))
            role_items = ([("staff", e) for e in emps]
                          + [("cand", e) for e in self._candidates(role)])
            if not role_items:
                lines.append(Text("  (cupo lleno)", style="grey62"))
            for kind, e in role_items:
                lines.append(self._emp_left_row(kind, e, idx == self._emp_sel))
                idx += 1
            lines.append(Text(""))
        return lines

    def _emp_left_row(self, kind, e, selected: bool) -> Text:
        mark = " " if kind == "staff" else "+"
        nb = len(e.bonuses)  # cuantos bonus trae (para leer de un vistazo el "build")
        text = f" {mark}{e.full_name:<19.19} {nb}b Pod {e.power:>3.0f} {money(e.weekly_wage)}"
        if selected:
            return Text(text[:_FAC_LEFT].ljust(_FAC_LEFT), style="bold black on green")
        return Text(text[:_FAC_LEFT], style="white" if kind == "staff" else "green")

    def _emp_detail_lines(self, club, today, items) -> list:
        """Columna derecha: detalle del item seleccionado (staff o candidato)."""
        lines = [Text("DETALLE", style="bold green")]
        if not items:
            lines.append(Text("Sin empleados ni candidatos.", style="grey62"))
            lines.append(Text("Subi de division para mas cupos.", style="grey62"))
            return lines
        kind, role, e = items[self._emp_sel]
        lines += [
            Text(e.full_name, style="bold white"),
            Text(role.value, style="white"),
            Text(f"Nacion: {e.nationality}   Edad: {e.age_on(today)}", style="grey70"),
            Text(f"Poder {e.power:.0f}    Sueldo {money(e.weekly_wage)}/sem", style="white"),
            Text(""),
            Text("Bonus:", style="grey70"),
        ]
        for btype, strength in e.bonuses.items():  # primario primero (orden de insercion)
            live = staff.is_live(btype)
            lines.append(Text(f"  {staff.bonus_desc(btype, strength)}",
                              style="grey70" if live else "grey50"))
        lines.append(Text(""))
        if kind == "staff":
            lines.append(Text("[Supr] despedir", style="red"))
        else:
            can = staff.can_hire(club, role)
            lines.append(Text(f"[Enter] contratar ({money(e.weekly_wage)}/sem)",
                              style="green" if can else "grey62"))
        return lines

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
