"""Seccion Club: la institucion.

Pestañas:
- Resumen: tablero + pantallazo (emblema, identidad, proximo partido, novedades).
- Notificaciones: registro de novedades y eventos accionables.
- Instalaciones: estadio y construcciones (plan en borrador).
- Empleados: cuerpo de trabajo (DT + roles), contratos y candidatos por rol.
"""

import copy

from rich.text import Text

from ...core.rng import new_rng
from ...domain.enums import EmployeeRole
from ...generators.coach_generator import CoachGenerator
from ...generators.employee_generator import EmployeeGenerator
from ...persistence import savegame
from ...simulation import facilities as fac
from ...simulation import notifications as notif
from ...simulation import staff
from ...simulation import training as tr
from ...simulation.economy import (
    membership_income, player_value, squad_wage_bill, stadium_upkeep)
from ...simulation.season import compute_standings
from ..format import append_section, hint, money
from ..identicon import emblem_lines
from .section_screen import SectionScreen

# Etiqueta corta de cada rol para la lista de la izquierda en Empleados.
_ROLE_SHORT = {
    EmployeeRole.DOCTOR: "Medico",
    EmployeeRole.FINANCE: "Dir. financiero",
    EmployeeRole.ASSISTANT: "Asistente tec.",
    EmployeeRole.PSYCHOLOGIST: "Psicologo",
}
# Roles que todavia no existen: se muestran como placeholder (con su detalle) para que
# se vea que vienen. Cada uno: (titulo, descripcion de que hara).
_FUTURE_ROLES = [
    ("Cazatalentos",
     "Ojeara juveniles para nutrir la Cantera (Complejo juvenil)."),
]
# Alto fijo del bloque de dos columnas de Empleados: empuja la ayuda al fondo del
# area de contenido, dejando una linea en blanco antes del menu inferior.
_STAFF_ROWS = 16
_EMP_LEFT = 24   # ancho de la columna de roles (izquierda)
_EMP_RIGHT = 54  # ancho del detalle del rol (derecha): 80 - _EMP_LEFT - "| "

# Color de cada estado de un edificio (para la lista de instalaciones).
_FAC_STYLE = {
    "buildable": "green", "upgradable": "white", "maxed": "grey70",
    "in_progress": "yellow", "locked_tier": "grey50", "locked_req": "grey50",
    "coming_soon": "grey50",
}
_FAC_LEFT = 40  # ancho de la columna izquierda (lista) en Instalaciones
_FAC_RIGHT = 38  # ancho de la columna derecha (detalle): 80 - _FAC_LEFT - "| "
_FAC_PAGE = 12  # edificios por pagina en la columna (paginada; escala al sumar edificios)
_FAC_ROWS = 16  # alto del bloque de dos columnas (empuja la ayuda al fondo, con aire)
# Color por categoria de notificacion (para leerlas de un vistazo).
_CAT_STYLE = {
    notif.FINANCE: "green", notif.MATCH: "cyan", notif.MARKET: "yellow",
    notif.TRAINING: "magenta", notif.SQUAD: "red", notif.GENERAL: "white",
}
_NOTIF_PAGE = 8  # notificaciones por pagina (2 lineas c/u) en la pestana


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
    tabs = ("Resumen", "Notificaciones", "Instalaciones", "Empleados")
    _NOTIF_TAB = 1  # indice de la pestana Notificaciones (interactiva)
    _FAC_TAB = 2    # indice de la pestana Instalaciones (interactiva)
    _STAFF_TAB = 3  # indice de la pestana Empleados (interactiva)

    def __init__(self) -> None:
        super().__init__()
        self._notif_sel = 0     # cursor en Notificaciones
        self._fac_sel = 0       # item seleccionado en Instalaciones (lista paginada)
        self._fac_plan: list = []  # cambios en borrador (se confirman con G)
        self._fac_msg = ""      # aviso (rechazo / confirmado)
        self._emp_role = 0      # rol seleccionado en Empleados (columna izquierda)
        self._emp_sel = 0       # persona seleccionada dentro del rol (columna derecha)

    @property
    def _club(self):
        game = self.app.game
        return game.player_club if game else None

    def render_tab(self, index: int) -> Text:
        if index == self._NOTIF_TAB:
            return self._notifications_text()
        if index == self._FAC_TAB:
            return self._facilities_text()
        if index == self._STAFF_TAB:
            return self._staff_text()
        return self._summary_text()

    def _summary_text(self) -> Text:
        club = self._club
        if club is None:
            return Text("Sin club todavia.", style="white")
        game = self.app.game
        today = game.calendar.current_date
        cap = f"{club.stadium.capacity:,}".replace(",", ".")
        manager = club.manager.full_name if club.manager else "-"

        # --- Cabecera a tres columnas: emblema | identidad | pantallazo ---
        identity = [
            "",
            (f"{club.name}  ({club.short_name})"[:30], "bold white"),
            (f"Liga {club.tier.value}   {club.country_code}   Temp {game.season}", "grey62"),
            (f"Manager: {manager}"[:30], "white"),
            (f"Estadio: {club.stadium.name}"[:30], "white"),
            (f"Socios: {club.members}", "grey70"),
            (f"Hinchada: {club.fans_name}"[:30], "grey70"),
        ]
        glance = self._glance_lines(club, game)  # 7 filas (texto, estilo) para cols 44-80
        t = Text()
        emblem = emblem_lines(club.name)
        emb_w = max(len(r.plain) for r in emblem)
        _GLANCE_COL = 44
        for i in range(len(emblem)):
            row = Text()
            row.append_text(emblem[i])
            row.append(" " * (emb_w - len(emblem[i].plain) + 2))
            text, style = identity[i] if isinstance(identity[i], tuple) else (identity[i], "white")
            row.append(text, style=style)
            t.append_text(row)
            t.append(" " * max(1, _GLANCE_COL - len(row.plain)))
            gtext, gstyle = glance[i]
            t.append(gtext[:80 - _GLANCE_COL] + "\n", style=gstyle)
        t.append("-" * 80 + "\n", style="grey50")

        # --- Datos para el tablero ---
        squad_value = sum(player_value(p, today) for p in club.players)
        injured = sum(1 for p in club.players if p.injury is not None)
        suspended = sum(1 for p in club.players if p.matches_suspended > 0)
        built = sum(1 for lv in club.facilities.values() if lv > 0)
        dues = membership_income(club.members)
        facs = fac.facility_income(club)
        spon = sum(s.weekly_pay for s in club.sponsors if s.active)
        gestion = round((dues + facs) * staff.income_bonus(club))
        wages = round(squad_wage_bill(club.players, today) * (1 - staff.wage_reduction(club)))
        net = (dues + facs + spon + gestion) - (
            wages + staff.staff_wage_bill(club) + stadium_upkeep(club.stadium.capacity))
        from ...simulation import sponsors as sp
        n_spon, slots = sum(1 for s in club.sponsors if s.active), sp.slots_for_tier(club.tier)
        assigned = sum(tr.group_counts(club).values())
        # Mercado y obras: un vistazo rapido (el detalle esta en sus pantallas).
        on_sale = sum(1 for p in club.players if p.asking_price is not None)
        n_offers = len(game.offers)
        works = club.constructions
        works_txt = (f"{len(works)} (prox {min(w.days_remaining for w in works)}d)"
                     if works else "ninguna")

        left = self._sec("PLANTEL", [
            ("OVR medio", str(club.overall)),
            ("Jugadores", str(len(club.players))),
            ("Valor plantel", money(squad_value)),
            ("Baja/Sancion", f"{injured} les.  {suspended} susp."),
        ]) + [Text("")] + self._sec("INSTALACIONES", [
            ("Construidas", f"{built}  (+{money(facs)}/sem)"),
            ("Capacidad", cap),
            ("Parcelas", f"{fac.plots_free(club)}/{club.plots} libres"),
            ("Obras", works_txt),
        ])
        right = self._sec("FINANZAS", [
            ("Caja", money(club.capital)),
            ("Patrimonio", money(club.capital + squad_value)),
            ("Semanal recur.", ("+" if net >= 0 else "-") + money(abs(net)),
             "green" if net >= 0 else "red"),
            ("Patrocinadores", f"{n_spon}/{slots} cupos"),
            ("Mercado", f"{on_sale} en venta, {n_offers} of."),
        ]) + [Text("")] + self._sec("STAFF Y ENTRENAMIENTO", [
            ("Empleados", f"{staff.role_count(club, EmployeeRole.DOCTOR)} med, "
                          f"{staff.role_count(club, EmployeeRole.FINANCE)} fin"),
            ("Sueldo staff", f"{money(staff.staff_wage_bill(club))}/sem"),
            ("Cap. entreno", f"{tr.capacity(club):.0f}  ({assigned} entrenando)"),
        ])
        for i in range(max(len(left), len(right))):
            lline = left[i] if i < len(left) else Text("")
            rline = right[i] if i < len(right) else Text("")
            t.append_text(lline)
            t.append(" " * max(0, 40 - len(lline.plain)))
            t.append_text(rline)
            t.append("\n")
        return t

    def _glance_lines(self, club, game) -> list:
        """Pantallazo (7 filas) al costado de la identidad: proximo partido con
        clima y tipo, posicion en la liga y ultima novedad."""
        from ...simulation.weather import forecast

        lines = [("PROXIMO PARTIDO", "bold green")]
        m = self._next_match()
        if m is None:
            lines += [("  Sin proximos partidos", "grey62"), ("", "white"), ("", "white")]
        else:
            rival = m.away if m.home is club else m.home
            sede = "Local" if m.home is club else "Visita"
            when = m.match_date.strftime("%d-%m") if m.match_date else f"J{m.matchday}"
            lines.append((f"  vs {rival.name}", "bold white"))
            lines.append((f"  {sede}  {when}  {m.kind.value}", "white"))
            lines.append((f"  Clima: {forecast(m, game.seed)}", "grey70"))
        pos = self._position()
        pos_txt = f"{pos[0]}/{pos[2]}  ({pos[1]} pts)" if pos else "-"
        lines.append((f"  Posicion liga: {pos_txt}", "grey70"))
        unread = notif.unread_count(game)
        hdr = "NOVEDADES" + (f"  ({unread} sin leer)" if unread else "")
        lines.append((hdr, "bold green"))
        recent = notif.recent(game, 1)
        lines.append((f"  {recent[0].subject}" if recent else "  (sin novedades)", "grey70"))
        return lines

    def _next_match(self):
        from datetime import date

        game = self.app.game
        club = self._club
        if club is None:
            return None
        league = game.player_league
        mine = [m for m in (league.matches if league else [])
                if m.home is club or m.away is club]
        mine += list(game.friendlies)
        pending = [m for m in mine if not m.played]
        if not pending:
            return None
        return min(pending, key=lambda m: (m.match_date or date.max, m.matchday))

    def _position(self):
        game = self.app.game
        league = game.player_league if game else None
        club = self._club
        if league is None or club is None:
            return None
        for pos, standing in enumerate(compute_standings(league), start=1):
            if standing.club is club:
                return pos, standing.points, len(league.clubs)
        return None

    def _sec(self, title: str, rows: list) -> list:
        """Un bloque del tablero: titulo + filas 'etiqueta valor' (sin blanco final;
        el aire entre secciones lo agrega quien concatena)."""
        out = [Text(title, style="bold green")]
        for row in rows:
            label, value = row[0], row[1]
            style = row[2] if len(row) > 2 else "white"
            line = Text(f"  {label:<15}", style="grey70")
            line.append(value, style=style)
            out.append(line)
        return out

    # --- Instalaciones (plan en borrador + lista paginada) ---
    def _fac_items(self) -> list:
        """Todos los items navegables: edificios del catalogo + gradas del estadio."""
        return ([("facility", s.id) for s in fac.CATALOG]
                + [("stand", sec) for sec in fac.STANDS])

    # --- Plan en borrador (proyeccion sobre una copia; el club real no se toca) ---
    def _apply_action(self, club, action) -> bool:
        if action[0] == "build":
            return fac.start_facility(club, action[1])
        if action[0] == "stand":
            return fac.start_stand(club, action[1])
        return fac.buy_plot(club)  # ("plot",)

    def _planned_club(self):
        base = self._club
        c = copy.copy(base)
        c.facilities = dict(base.facilities)
        c.constructions = list(base.constructions)
        for act in self._fac_plan:
            self._apply_action(c, act)
        return c

    def _item_action(self, kind, key):
        return ("build", key) if kind == "facility" else ("stand", key)

    def _plan_has(self, kind, key) -> bool:
        return self._item_action(kind, key) in self._fac_plan

    def _stage(self, action) -> None:
        if self._apply_action(self._planned_club(), action):
            self._fac_plan.append(action)
            self._fac_msg = ""
        else:
            self._fac_msg = "No se puede: falta plata, parcela o no corresponde."

    def _unstage_item(self, kind, key) -> None:
        act = self._item_action(kind, key)
        if act in self._fac_plan:
            self._fac_plan.remove(act)
            self._revalidate()
            self._fac_msg = ""

    def _unstage_plot(self) -> None:
        for i in range(len(self._fac_plan) - 1, -1, -1):
            if self._fac_plan[i] == ("plot",):
                del self._fac_plan[i]
                self._revalidate()
                self._fac_msg = ""
                return

    def _revalidate(self) -> None:
        """Deja en el plan solo las acciones que siguen aplicando (en orden)."""
        base = self._club
        c = copy.copy(base)
        c.facilities = dict(base.facilities)
        c.constructions = list(base.constructions)
        self._fac_plan = [a for a in self._fac_plan if self._apply_action(c, a)]

    def _confirm(self) -> None:
        if not self._fac_plan:
            self._fac_msg = "No hay cambios para confirmar."
            return
        from ...simulation.finance_log import record_movement

        club = self._club
        when = self.app.game.calendar.current_date
        n = len(self._fac_plan)
        for act in self._fac_plan:  # aplicar y registrar el gasto en el libro de caja
            before = club.capital
            if self._apply_action(club, act):
                spent = before - club.capital
                if spent:
                    record_movement(club, when, self._action_label(act), -spent)
        self._fac_plan = []
        savegame.save_game(self.app.game)
        self._fac_msg = f"{n} cambio(s) confirmado(s)."

    def _action_label(self, action) -> str:
        if action[0] == "build":
            return f"Obra: {fac.spec(action[1]).name}"
        if action[0] == "stand":
            return f"Grada: {fac.stand_label(action[1])}"
        return "Compra de parcela"

    def _reset(self) -> None:
        self._fac_plan = []
        self._fac_msg = ""

    # --- Render ---
    def _facilities_text(self) -> Text:
        club = self._club
        if club is None:
            return Text("Sin club todavia.", style="white")
        items = self._fac_items()
        self._fac_sel = max(0, min(len(items) - 1, self._fac_sel))
        planned = self._planned_club() if self._fac_plan else club
        pages = max(1, (len(items) + _FAC_PAGE - 1) // _FAC_PAGE)
        page = self._fac_sel // _FAC_PAGE

        t = Text()
        t.append("INSTALACIONES   ", style="bold green")
        if self._fac_plan:
            t.append(f"Caja {money(club.capital)}->{money(planned.capital)}   ", style="white")
            t.append(f"Parc {fac.plots_free(club)}/{club.plots}->"
                     f"{fac.plots_free(planned)}/{planned.plots}   ", style="grey70")
        else:
            t.append(f"Caja {money(club.capital)}   ", style="white")
            t.append(f"Parc {fac.plots_free(club)}/{club.plots}   ", style="grey70")
        t.append(f"Parcela {money(fac.plot_cost(planned))}\n", style="grey70")
        t.append("-" * 80 + "\n", style="grey50")

        left = self._fac_left_lines(club, items, page)
        # La paginacion va centrada al pie de la columna de edificios (ultima fila con "|"),
        # asi no alarga el encabezado (que hace wrap con los valores proyectados).
        while len(left) < _FAC_ROWS - 2:
            left.append(Text(""))
        left.append(Text(f"Pag {page + 1}/{pages}".center(_FAC_LEFT), style="grey62")
                    if pages > 1 else Text(""))
        right = self._fac_detail_lines(club, planned, items)
        for i in range(_FAC_ROWS):
            if i == _FAC_ROWS - 1:
                t.append("\n")   # ultima fila en blanco: separa la ayuda del menu
                continue
            lline = left[i] if i < len(left) else Text("")
            rline = right[i] if i < len(right) else Text("")
            t.append_text(lline)
            t.append(" " * max(0, _FAC_LEFT - len(lline.plain)))
            t.append("| ", style="grey50")
            t.append_text(rline)
            t.append("\n")
        t.append_text(hint(("^v", "mover"), ("<>", "pagina"), ("Enter", "plan"),
                           ("+/-", "parcela"), ("G", "confirmar"), ("Esc", "descartar"),
                           sep="  "))
        return t

    def _fac_left_lines(self, club, items, page) -> list:
        start = page * _FAC_PAGE
        return [self._fac_row(club, idx, kind, key)
                for idx, (kind, key) in list(enumerate(items))[start:start + _FAC_PAGE]]

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
            name = s.name
        else:
            seats, _cost, _days, mt = fac.STANDS[key]
            status = fac.stand_status(club, key)
            tag = {"buildable": f"+{seats}", "in_progress": "(obra)",
                   "locked_tier": f"(Liga {mt.value})"}[status]
            style = {"buildable": "green", "in_progress": "yellow",
                     "locked_tier": "grey50"}[status]
            name = fac.stand_label(key)
        plan = " [plan]" if self._plan_has(kind, key) else ""
        text = f" {name:<20.20} {tag:<9}{plan}"
        if idx == self._fac_sel:
            return Text(text[:_FAC_LEFT].ljust(_FAC_LEFT), style="bold black on green")
        return Text(text[:_FAC_LEFT], style="yellow" if plan else style)

    def _fac_detail_lines(self, club, planned, items) -> list:
        lines = [Text("DETALLE", style="bold green")]
        if not items:
            lines.append(Text("Nada en esta categoria.", style="grey62"))
            return lines
        kind, key = items[self._fac_sel]
        staged = self._plan_has(kind, key)
        if kind == "facility":
            lines += self._fac_detail_facility(club, key, staged)
        else:
            lines += self._fac_detail_stand(club, key, staged)
        lines.append(Text(""))
        if self._fac_plan:
            lines.append(Text(f"PLAN: {len(self._fac_plan)} cambio(s)  "
                              f"-{money(club.capital - planned.capital)}",
                              style="bold yellow"))
        if self._fac_msg:
            for wl in _wrap(self._fac_msg, _FAC_RIGHT - 2):
                lines.append(Text(wl, style="grey70"))
        return lines

    def _plan_action_line(self, staged: bool) -> Text:
        return (Text("[Enter] sacar del plan", style="yellow") if staged
                else Text("[Enter] agregar al plan", style="green"))

    def _fac_detail_facility(self, club, key, staged) -> list:
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
        special = fac.facility_effect_desc(key)
        if special:
            lines.append(Text("Efecto x nivel:", style="grey70"))
            for wl in _wrap(special, _FAC_RIGHT - 2):
                lines.append(Text(f"  {wl}", style="grey70"))
        else:
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
            extra = f", {s.plots} parcela" if lv == 0 else ""
            verb = "Construir" if lv == 0 else f"Mejorar a Nv{target}"
            lines.append(Text(f"{verb}: {money(cost)} ({s.build_days}d{extra})", style="white"))
            lines.append(self._plan_action_line(staged))
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

    def _fac_detail_stand(self, club, key, staged) -> list:
        seats, cost, days, mt = fac.STANDS[key]
        status = fac.stand_status(club, key)
        lines = [Text(f"{fac.stand_label(key)}  (+{seats} asientos)", style="bold white")]
        if status == "buildable" or staged:
            lines.append(Text(f"Construir: {money(cost)} ({days}d, 1 parcela)", style="white"))
            lines.append(self._plan_action_line(staged))
        elif status == "locked_tier":
            lines.append(Text(f"Necesita liga {mt.value} o mejor", style="grey62"))
        else:
            lines.append(Text("Ya hay una obra de esta grada", style="yellow"))
        return lines

    # --- Teclado (pestanas interactivas: Instalaciones y Empleados) ---
    def on_content_key(self, event) -> None:
        if self._active_tab == self._NOTIF_TAB:
            self._notif_key(event)
            return
        if self._club is None:
            return
        if self._active_tab == self._FAC_TAB:
            self._facilities_key(event)
        elif self._active_tab == self._STAFF_TAB:
            self._staff_key(event)

    def _facilities_key(self, event) -> None:
        # OJO: 'g' no es letra de seccion (o/c/j/p/e/f), asi que llega aca para confirmar.
        key, ch = event.key, event.character
        items = self._fac_items()
        if key == "up":
            event.stop(); self._fac_sel = max(0, self._fac_sel - 1); self._refresh_content()
        elif key == "down":
            event.stop(); self._fac_sel = min(len(items) - 1, self._fac_sel + 1); self._refresh_content()
        elif key in ("left", "pageup"):
            event.stop(); self._fac_sel = max(0, self._fac_sel - _FAC_PAGE); self._refresh_content()
        elif key in ("right", "pagedown"):
            event.stop(); self._fac_sel = min(len(items) - 1, self._fac_sel + _FAC_PAGE); self._refresh_content()
        elif key == "enter":
            event.stop()
            if items:
                kind, k = items[self._fac_sel]
                if self._plan_has(kind, k):
                    self._unstage_item(kind, k)
                else:
                    self._stage(self._item_action(kind, k))
                self._refresh_content()
        elif ch == "+":
            event.stop(); self._stage(("plot",)); self._refresh_content()
        elif ch == "-":
            event.stop(); self._unstage_plot(); self._refresh_content()
        elif ch in ("g", "G"):
            event.stop(); self._confirm(); self._refresh_content()
        elif key == "escape":
            event.stop(); self._reset(); self._refresh_content()

    def on_tab_shown(self, index: int) -> None:
        # Al entrar a Notificaciones se marcan leidas las informativas (baja el badge).
        if index == self._NOTIF_TAB and self.app.game is not None:
            notif.mark_all_read(self.app.game)
            self._refresh_topbar()
        # Al salir de Instalaciones, se descartan los cambios en borrador no confirmados.
        if index != self._FAC_TAB and self._fac_plan:
            self._reset()

    # --- Notificaciones (lista navegable + apertura de eventos accionables) ---
    def _notif_key(self, event) -> None:
        game = self.app.game
        if game is None:
            return
        total = len(notif.all_newest_first(game))
        key = event.key
        if key == "up":
            event.stop(); self._notif_sel = max(0, self._notif_sel - 1); self._refresh_content()
        elif key == "down":
            event.stop(); self._notif_sel = min(total - 1, self._notif_sel + 1); self._refresh_content()
        elif key in ("left", "pageup"):
            event.stop(); self._notif_sel = max(0, self._notif_sel - _NOTIF_PAGE); self._refresh_content()
        elif key in ("right", "pagedown"):
            event.stop(); self._notif_sel = min(total - 1, self._notif_sel + _NOTIF_PAGE); self._refresh_content()
        elif key == "enter":
            event.stop(); self._open_event()

    def _open_event(self) -> None:
        """Abre el evento seleccionado (si es accionable). Despacha por `kind`."""
        game = self.app.game
        items = notif.all_newest_first(game)
        if not (0 <= self._notif_sel < len(items)):
            return
        n = items[self._notif_sel]
        if n.kind == notif.EVENT_SPONSOR_OFFER and n.status == "pending":
            from .sponsor_offer_screen import SponsorOfferScreen

            self.app.push_screen(SponsorOfferScreen(game, n, on_close=self._on_event_closed))

    def _on_event_closed(self) -> None:
        self._refresh_content()
        self._refresh_topbar()

    def _notifications_text(self) -> Text:
        game = self.app.game
        items = notif.all_newest_first(game) if game else []
        t = Text()
        if not items:
            append_section(t, "NOTIFICACIONES", [
                ("Todavia no hay notificaciones.", "grey62"),
                ("Aca vas a ver el cierre economico, resultados, fichajes,", "grey62"),
                ("las ofertas de patrocinio y demas novedades del club.", "grey62"),
            ])
            return t
        self._notif_sel = max(0, min(len(items) - 1, self._notif_sel))
        pages = max(1, (len(items) + _NOTIF_PAGE - 1) // _NOTIF_PAGE)
        page = self._notif_sel // _NOTIF_PAGE
        rows = list(enumerate(items))[page * _NOTIF_PAGE: page * _NOTIF_PAGE + _NOTIF_PAGE]

        t.append("NOTIFICACIONES", style="bold green")
        t.append(f"   ({len(items)} en total)", style="grey50")
        if pages > 1:
            t.append(f"   Pag {page + 1}/{pages}", style="grey62")
        t.append("\n")
        t.append("-" * 80 + "\n", style="grey50")
        for i, n in rows:
            self._append_notif(t, n, i == self._notif_sel)
        t.append("\n" * max(0, _NOTIF_PAGE - len(rows)) * 2)  # relleno para dejar aire
        t.append_text(hint(("arr/aba", "elegir"), ("izq/der", "pagina"),
                           ("Enter", "abrir evento")))
        return t

    def _append_notif(self, t: Text, n, selected: bool) -> None:
        when = n.date.strftime("%d-%m-%Y")
        pending = n.is_pending_event
        mark = "[!]" if pending else "   "
        style = "bold yellow" if pending else _CAT_STYLE.get(n.category, "white")
        head = f"{mark} {when}  {n.subject}"
        if selected:
            t.append(("> " + head)[:80].ljust(80) + "\n", style="bold black on green")
        else:
            t.append(mark + " ", style="yellow" if pending else "grey50")
            t.append(f"{when}  ", style="grey50")
            t.append(n.subject + "\n", style=style)
        t.append(f"          {n.message}"[:80] + "\n", style="grey70")

    def _staff_key(self, event) -> None:
        # OJO: el frame se queda con las letras de seccion (c/j/p/e/f) antes de
        # llegar aca, por eso "contratar/reemplazar" va en Enter y "despedir" en
        # Supr/Retroceso/'d'. Izq/der cambian de rol; arriba/abajo, de persona.
        key = event.key
        roles = self._emp_roles()
        if key == "left":
            event.stop(); self._emp_role = max(0, self._emp_role - 1); self._emp_sel = 0
            self._refresh_content(); return
        if key == "right":
            event.stop(); self._emp_role = min(len(roles) - 1, self._emp_role + 1); self._emp_sel = 0
            self._refresh_content(); return
        entry = roles[self._emp_role]
        people = self._emp_people(entry)
        if key == "up":
            event.stop(); self._emp_sel = max(0, self._emp_sel - 1); self._refresh_content()
        elif key == "down":
            event.stop(); self._emp_sel = min(max(0, len(people) - 1), self._emp_sel + 1); self._refresh_content()
        elif key == "enter":
            event.stop(); self._emp_hire(entry, people)
        elif key in ("delete", "backspace") or event.character in ("d", "D"):
            event.stop(); self._emp_fire(entry, people)

    def _emp_hire(self, entry, people) -> None:
        """Enter: contrata un candidato de empleado o reemplaza al DT."""
        if not (0 <= self._emp_sel < len(people)):
            return
        kind, obj = people[self._emp_sel]
        if kind == "coach_cand":
            staff.replace_coach(self.app.game, obj)
        elif kind == "cand" and staff.hire(self.app.game, obj):
            pass
        else:
            return
        savegame.save_game(self.app.game)
        self._refresh_content()

    def _emp_fire(self, entry, people) -> None:
        """Supr: despide al empleado seleccionado (el DT no se despide, se reemplaza)."""
        if not (0 <= self._emp_sel < len(people)):
            return
        kind, obj = people[self._emp_sel]
        if kind == "staff":
            staff.fire(self.app.game, obj)
            self._emp_sel = max(0, self._emp_sel - 1)
            savegame.save_game(self.app.game)
            self._refresh_content()

    # --- Modelo de la pestana Empleados (roles a la izquierda, personas a la derecha) ---
    def _emp_roles(self) -> list:
        """Entradas de la columna de roles: DT + roles reales + placeholders futuros."""
        entries = [("coach", None)]
        entries += [("role", role) for role in EmployeeRole]
        entries += [("future", i) for i in range(len(_FUTURE_ROLES))]
        return entries

    def _emp_people(self, entry) -> list:
        """Personas navegables del rol elegido: (kind, obj). Vacio para roles futuros."""
        club = self._club
        kind, ref = entry
        if kind == "coach":
            people = [("coach_cur", club.coach)] if club.coach else []
            people += [("coach_cand", c) for c in self._coach_candidates()]
            return people
        if kind == "role":
            return ([("staff", e) for e in staff.employees_of(club, ref)]
                    + [("cand", e) for e in self._candidates(ref)])
        return []

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

    def _coach_candidates(self) -> list:
        """Terna de DTs para reemplazar al actual (determinista, estable en el dia)."""
        club = self._club
        today = self.app.game.calendar.current_date
        gen = CoachGenerator(new_rng(self.app.game.seed + today.toordinal() + 999))
        return [gen.generate(club.country_code, club.tier, today) for _ in range(3)]

    def _staff_text(self) -> Text:
        club = self._club
        if club is None:
            return Text("Sin club todavia.", style="white")
        today = self.app.game.calendar.current_date
        roles = self._emp_roles()
        self._emp_role = max(0, min(len(roles) - 1, self._emp_role))
        entry = roles[self._emp_role]
        people = self._emp_people(entry)
        self._emp_sel = max(0, min(len(people) - 1, self._emp_sel)) if people else 0

        t = Text()
        t.append("EMPLEADOS   ", style="bold green")
        t.append(f"Sueldos {money(staff.staff_wage_bill(club))}/sem   "
                 f"(incluye al DT)\n", style="grey70")
        t.append("-" * 80 + "\n", style="grey50")

        left = self._emp_role_lines(club, roles)
        right = self._emp_detail_lines(club, today, entry, people)
        for i in range(_STAFF_ROWS):
            if i == _STAFF_ROWS - 1:
                t.append("\n")   # ultima fila en blanco: separa la ayuda del menu (sin "|")
                continue
            lline = left[i] if i < len(left) else Text("")
            rline = right[i] if i < len(right) else Text("")
            t.append_text(lline)
            t.append(" " * max(0, _EMP_LEFT - len(lline.plain)))
            t.append("| ", style="grey50")
            t.append_text(rline)
            t.append("\n")
        t.append_text(self._emp_hint(entry))
        return t

    def _emp_hint(self, entry):
        kind = entry[0]
        if kind == "coach":
            return hint(("<>", "rol"), ("^v", "elegir"), ("Enter", "reemplazar DT"))
        if kind == "future":
            return hint(("<>", "rol"))
        return hint(("<>", "rol"), ("^v", "elegir"), ("Enter", "contratar"),
                    ("Supr", "despedir"))

    def _emp_role_lines(self, club, roles) -> list:
        """Columna izquierda: la lista de roles con su cupo; resalta el activo."""
        lines = [Text("ROLES", style="bold green")]
        for idx, (kind, ref) in enumerate(roles):
            if kind == "coach":
                label = f"DT {club.coach.last_name}" if club.coach else "DT"
                cupo = "1/1"
            elif kind == "role":
                label = _ROLE_SHORT[ref]
                cupo = f"{staff.role_count(club, ref)}/{staff.staff_slots(club, ref)}"
            else:
                label = _FUTURE_ROLES[ref][0]
                cupo = "prox"
            text = f" {label:<15.15}{cupo:>6}"
            if idx == self._emp_role:
                lines.append(Text(text[:_EMP_LEFT].ljust(_EMP_LEFT), style="bold black on green"))
            else:
                style = "grey50" if kind == "future" else "white"
                lines.append(Text(text[:_EMP_LEFT], style=style))
        return lines

    def _emp_detail_lines(self, club, today, entry, people) -> list:
        """Columna derecha: detalle del rol elegido (contratados + candidatos)."""
        kind = entry[0]
        if kind == "future":
            return self._emp_future_lines(entry[1])
        if kind == "coach":
            return self._emp_coach_lines(club, today, people)
        return self._emp_role_detail_lines(club, today, entry[1], people)

    def _emp_future_lines(self, i) -> list:
        label, desc = _FUTURE_ROLES[i]
        lines = [Text(label.upper(), style="bold green"), Text("Rol futuro", style="grey70"),
                 Text("")]
        for wl in _wrap(desc, _EMP_RIGHT - 1):
            lines.append(Text(wl, style="grey62"))
        lines.append(Text(""))
        lines.append(Text("Se implementara con la Cantera.", style="yellow"))
        return lines

    def _emp_coach_lines(self, club, today, people) -> list:
        lines = [self._emp_head("DIRECTOR TECNICO", "1/1")]
        for i, (kind, c) in enumerate(people):
            if kind == "coach_cur":
                lines.append(Text("Actual:", style="grey70"))
            elif i == 1:
                lines.append(Text("Reemplazar por:", style="grey70"))
            lines.append(self._emp_coach_row(c, i == self._emp_sel, kind == "coach_cur"))
        # Detalle del seleccionado + accion.
        lines.append(Text(""))
        if 0 <= self._emp_sel < len(people):
            kind, c = people[self._emp_sel]
            lines.append(Text(f"Ment: {c.mentality.value}   Edad: {c.age_on(today)}",
                              style="grey70"))
            if kind == "coach_cand":
                lines.append(Text(f"[Enter] reemplazar DT ({money(staff.coach_wage(c, club.tier))}/sem)",
                                  style="green"))
            else:
                lines.append(Text("Es tu DT actual.", style="grey62"))
        return lines

    def _emp_coach_row(self, c, selected: bool, current: bool) -> Text:
        wage = staff.coach_wage(c, self._club.tier)
        mark = " " if current else "+"
        text = f" {mark}{c.full_name:<20.20} Hab {c.skill:>4.1f} Lid {c.leadership:>4.1f} {money(wage)}"
        if selected:
            return Text(text[:_EMP_RIGHT].ljust(_EMP_RIGHT), style="bold black on green")
        return Text(text[:_EMP_RIGHT], style="white" if current else "green")

    def _emp_role_detail_lines(self, club, today, role, people) -> list:
        slots = staff.staff_slots(club, role)
        lines = [self._emp_head(role.value.upper(), f"{staff.role_count(club, role)}/{slots}")]
        shown_hire_hdr = False
        for i, (kind, e) in enumerate(people):
            if kind == "staff" and i == 0:
                lines.append(Text("Contratados:", style="grey70"))
            if kind == "cand" and not shown_hire_hdr:
                lines.append(Text("Para contratar:", style="grey70"))
                shown_hire_hdr = True
            lines.append(self._emp_person_row(kind, e, i == self._emp_sel))
        if not people:
            lines.append(Text("Sin candidatos (cupo lleno).", style="grey62"))
        # Detalle (bonus) del seleccionado + accion.
        lines.append(Text(""))
        if 0 <= self._emp_sel < len(people):
            kind, e = people[self._emp_sel]
            lines.append(Text(f"Bonus de {e.full_name:.28}:", style="grey70"))
            for btype, strength in e.bonuses.items():  # primario primero
                live = staff.is_live(btype)
                lines.append(Text(f"  {staff.bonus_desc(btype, strength)}",
                                  style="grey70" if live else "grey50"))
            if kind == "staff":
                lines.append(Text("[Supr] despedir", style="red"))
            else:
                can = staff.can_hire(club, role)
                lines.append(Text(f"[Enter] contratar ({money(e.weekly_wage)}/sem)",
                                  style="green" if can else "grey62"))
        return lines

    def _emp_person_row(self, kind, e, selected: bool) -> Text:
        mark = " " if kind == "staff" else "+"
        nb = len(e.bonuses)  # cuantos bonus trae (para leer el "build" de un vistazo)
        text = f" {mark}{e.full_name:<22.22} {nb}b Pod {e.power:>3.0f} {money(e.weekly_wage)}"
        if selected:
            return Text(text[:_EMP_RIGHT].ljust(_EMP_RIGHT), style="bold black on green")
        return Text(text[:_EMP_RIGHT], style="white" if kind == "staff" else "green")

    def _emp_head(self, title: str, cupo: str) -> Text:
        """Encabezado del detalle: titulo del rol a la izquierda + cupo a la derecha."""
        head = Text(f"{title} ", style="bold green")
        pad = max(1, _EMP_RIGHT - len(title) - 1 - len(f"{cupo} cupos"))
        head.append(" " * pad + f"{cupo} cupos", style="grey62")
        return head

