"""Seccion Oficina: el dashboard "de un pantallazo".

Pestañas:
- Resumen: proximo partido, posicion en la liga, estado del club y las ultimas
  notificaciones (con el total sin leer).
- Notificaciones: el registro completo de novedades (subject + mensaje + fecha).
  Al abrir esta pestaña, las no leidas quedan marcadas como leidas.
- Semana: el ciclo semanal del juego (eventos por dia).
"""

from rich.text import Text

from ...simulation import notifications as notif
from ...simulation.season import compute_standings
from ..format import append_section, hint, money
from .section_screen import SectionScreen

# Color por categoria de notificacion (para leerlas de un vistazo).
_CAT_STYLE = {
    notif.FINANCE: "green", notif.MATCH: "cyan", notif.MARKET: "yellow",
    notif.TRAINING: "magenta", notif.SQUAD: "red", notif.GENERAL: "white",
}
_NOTIF_TAB = 1     # indice de la pestaña Notificaciones
_NOTIF_PAGE = 8    # notificaciones por pagina (2 lineas c/u) en la pestaña


class OfficeScreen(SectionScreen):
    """Dashboard inicial del manager."""

    section_key = "O"
    section_title = "Oficina"
    tabs = ("Resumen", "Notificaciones", "Semana")

    def __init__(self) -> None:
        super().__init__()
        self._notif_sel = 0  # cursor en la lista de Notificaciones

    # --- Datos ---
    @property
    def _game(self):
        return self.app.game

    def _next_match(self):
        from datetime import date

        game = self._game
        club = game.player_club if game else None
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
        if index == _NOTIF_TAB:
            return self._notifications_text()
        if index == 2:
            return self._week_text()
        return self._summary_text()

    def on_tab_shown(self, index: int) -> None:
        # Al entrar a Notificaciones se dan por leidas las INFORMATIVAS (los eventos
        # pendientes siguen avisando hasta que el manager los resuelva).
        if index == _NOTIF_TAB and self._game is not None:
            notif.mark_all_read(self._game)
            self._refresh_topbar()

    def on_content_key(self, event) -> None:
        if self._active_tab != _NOTIF_TAB or self._game is None:
            return
        total = len(notif.all_newest_first(self._game))
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
            event.stop(); self._open_selected()

    def _open_selected(self) -> None:
        """Abre el evento seleccionado (si es accionable). Despacha por `kind`."""
        items = notif.all_newest_first(self._game)
        if not (0 <= self._notif_sel < len(items)):
            return
        n = items[self._notif_sel]
        if n.kind == notif.EVENT_SPONSOR_OFFER and n.status == "pending":
            from .sponsor_offer_screen import SponsorOfferScreen

            self.app.push_screen(SponsorOfferScreen(self._game, n, on_close=self._on_event_closed))

    def _on_event_closed(self) -> None:
        self._refresh_content()
        self._refresh_topbar()

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
            when = m.match_date.strftime("%d-%m-%Y") if m.match_date else f"J{m.matchday}"
            tactic = "Si" if m.tactic is not None else "No"
            match_rows = [
                (f"Jornada {m.matchday}  -  {when}  -  {m.kind.value}", "bold white"),
                f"{club.name}  vs  {rival.name}   ({sede})",
                (f"Tactica asignada: {tactic}",
                 "green" if m.tactic is not None else "grey62"),
            ]
        append_section(t, "PROXIMO PARTIDO", match_rows)

        # Liga + club, en una linea de dos columnas para aprovechar el ancho.
        pos = self._position()
        pos_txt = f"{pos[0]}o de {pos[2]}   ({pos[1]} pts)" if pos else "-"
        append_section(t, "SITUACION", [
            f"Posicion en la liga: {pos_txt}",
            f"Caja: {money(club.capital):<18} Socios: {club.members}",
        ])

        # Ultimas notificaciones (con el total sin leer).
        game = self._game
        unread = notif.unread_count(game)
        title = "ULTIMAS NOTIFICACIONES"
        if unread:
            title += f"   ({unread} sin leer)"
        recent = notif.recent(game, 5)
        if not recent:
            rows = [("(sin novedades por ahora)", "grey62")]
        else:
            rows = [self._notif_summary_row(n) for n in recent]
            rows.append("")
            rows.append(("Mira todo en la pestana Notificaciones.", "grey50"))
        append_section(t, title, rows)
        return t

    def _notif_summary_row(self, n) -> tuple[str, str]:
        """Fila compacta de una notificacion para el Resumen (fecha + asunto)."""
        when = n.date.strftime("%d-%m")
        mark = " " if n.read else "*"  # sin leer -> asterisco
        style = _CAT_STYLE.get(n.category, "white")
        return (f"{mark} {when}  {n.subject}", style if not n.read else "grey62")

    def _notifications_text(self) -> Text:
        game = self._game
        items = notif.all_newest_first(game)
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
        # relleno + ayuda al fondo (una linea antes del menu)
        t.append("\n" * max(0, _NOTIF_PAGE - len(rows)) * 2)
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

    def _week_text(self) -> Text:
        # El ciclo semanal: que se procesa cada dia al avanzar el calendario.
        t = Text()
        append_section(t, "LA SEMANA", [
            ("Al avanzar el dia se procesa el evento que le toca:", "grey62"),
            "",
            ("Lun  Reaccion de los hinchas al partido", "grey70"),
            ("Mar  Dia libre", "grey70"),
            ("Mie  Mercado de pases y amistoso", "grey70"),
            ("Jue  Entrenamiento", "grey70"),
            ("Vie  Cierre economico (cobros y pagos)", "grey70"),
            ("Dom  Fecha de liga", "grey70"),
        ])
        return t
