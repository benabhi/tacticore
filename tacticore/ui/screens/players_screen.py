"""Seccion Jugadores: la plantilla, la cantera y el mercado.

Pestañas:
- Plantilla: la tabla del plantel (interactiva: se navega y se abre la ficha).
- Cantera: juveniles (placeholder; los alimentaran los cazatalentos).
- Mercado: transferencias in/out (placeholder).

La Plantilla es la unica pestaña interactiva: recibe el teclado en `on_content_key`
(flechas para moverse, Enter para la ficha, "/" para buscar en vivo, "m" para
marcar un jugador y comparar con otro). Las demas teclas del marco (numeros/Tab
para pestañas, letras para secciones) las maneja `SectionScreen`.
"""

from rich.text import Text

from ...domain.enums import Specialty
from ...domain.player import (
    ALL_ATTRS, MENTAL_ATTRS, PHYSICAL_ATTRS, TECHNICAL_ATTRS)
from ...domain.transfer import COUNTERED, PENDING
from ...persistence import savegame
from ...simulation import transfers as T
from ...simulation import youth
from ..format import append_section, hint, money
from ..player_labels import (
    ATTR_GROUPS, ATTR_LABEL, ATTR_SHORT, FOOT_SHORT, SPECIALTY_LABEL,
    SPECIALTY_SHORT)
from .section_screen import SectionScreen


def _attr_color(value: float) -> str:
    """Color de un atributo por su nivel (gradiente verde -> rojo), como en la ficha."""
    if value >= 80:
        return "bold green"
    if value >= 65:
        return "green"
    if value >= 50:
        return "yellow"
    if value >= 35:
        return "orange1"
    return "red"


def _mk_attr_key(attr: str):
    return lambda p, today: getattr(p, attr)


# Campos por los que se puede ordenar la plantilla, agrupados en 5 columnas (para el
# selector en grilla). Cada campo: (id, etiqueta, funcion(player, today) -> valor
# comparable). La especialidad se ordena por su sigla ("-" para los sin especialidad).
_SORT_GROUPS = [
    ("RENDIMIENTO", [
        ("ovr", "OVR", lambda p, t: p.overall),
        ("pot", "POT", lambda p, t: p.potential),
        ("form", "Forma", lambda p, t: p.form),
        ("fit", "Fitness", lambda p, t: p.fitness),
    ]),
    ("PERFIL", [
        ("age", "Edad", lambda p, t: p.age_on(t)),
        ("morale", "Moral", lambda p, t: p.morale.value),
        ("specialty", "Especialidad",
         lambda p, t: SPECIALTY_SHORT[p.specialty] if p.specialty else "-"),
        ("name", "Nombre", lambda p, t: p.last_name.lower()),
        ("pos", "Posicion", lambda p, t: p.position.value),
        ("shirt", "Dorsal", lambda p, t: p.shirt_number or 0),
    ]),
    ("FISICOS", [(a, ATTR_LABEL[a], _mk_attr_key(a)) for a in PHYSICAL_ATTRS]),
    ("TECNICOS", [(a, ATTR_LABEL[a], _mk_attr_key(a)) for a in TECHNICAL_ATTRS]),
    ("MENTALES", [(a, ATTR_LABEL[a], _mk_attr_key(a)) for a in MENTAL_ATTRS]),
]
_SORT_BY_ID = {fid: (label, fn) for _g, fields in _SORT_GROUPS for fid, label, fn in fields}
_SORT_TEXT = {"name", "pos"}   # campos de texto: por defecto ascendente (alfabetico)

_WIDTH = 80       # ancho total de la tabla (toda la pantalla)
_PAGE_SIZE = 14   # filas de jugadores por pagina
_MKT_PAGE = 10    # listados por pagina en el Mercado (deja lugar a "Mis ofertas")
_PEEK_PAGE = 8    # filas de jugadores cuando el panel de atributos esta abierto
_PLANTILLA, _CANTERA, _MERCADO = 0, 1, 2  # indices de pestañas interactivas
_YTH_LEFT = 28   # ancho de la columna de prospectos (Cantera)
_YTH_RIGHT = 49  # ancho del detalle (Cantera): 80 - _YTH_LEFT - "| "

# Columnas: (titulo, ancho, alineacion). El nombre se calcula para llenar los 80.
# EST = estado/disponibilidad (L#=lesionado con semanas, SUS=suspendido, 1A=una
# amarilla, - =disponible).
_NAME_W = _WIDTH - 2 - 12 - 36
_COLUMNS = [
    ("#", 2, "r"), ("NOMBRE", _NAME_W, "l"), ("POS", 3, "l"), ("NAC", 3, "l"),
    ("ED", 2, "r"), ("PIE", 3, "l"), ("OVR", 3, "r"), ("POT", 3, "r"),
    ("FOR", 3, "r"), ("FIT", 3, "r"), ("MOR", 3, "r"), ("ESP", 4, "l"),
    ("EST", 4, "l"),
]
_MOR_IDX = 10
_ESP_IDX = 11
_EST_IDX = 12

# Color de la moral (1 peor -> 5 mejor): de rojo a verde, sin leyenda aparte.
_MORALE_STYLE = {1: "bold red", 2: "red", 3: "yellow", 4: "green", 5: "bold green"}

# Columnas de la tabla del Mercado. CLUB llena el resto de los 80.
_MKT_CLUB_W = _WIDTH - 2 - (2 + 20 + 3 + 3 + 2 + 9) - 6
_MKT_COLS = [
    ("#", 2, "r"), ("NOMBRE", 20, "l"), ("POS", 3, "l"), ("OVR", 3, "r"),
    ("ED", 2, "r"), ("PRECIO", 9, "r"), ("CLUB", _MKT_CLUB_W, "l"),
]


class PlayersScreen(SectionScreen):
    """Plantilla del club (interactiva) + cantera y mercado (placeholder)."""

    section_key = "J"
    section_title = "Jugadores"
    tabs = ("Plantilla", "Cantera", "Mercado")

    def __init__(self) -> None:
        super().__init__()
        self._selected = 0    # indice del jugador seleccionado (sobre los visibles)
        self._searching = False  # si esta activo el buscador (se escribe)
        self._query = ""      # texto del filtro en vivo
        self._compare_from = None  # jugador marcado para comparar (A); None si no hay
        self._releasing = None  # jugador a confirmar despido (None = no hay confirmacion)
        self._peek = False     # panel de atributos inline abierto (vistazo rapido)
        # --- Orden de la plantilla ---
        self._sort_key = None  # id del campo por el que se ordena (None = orden de plantel)
        self._sort_desc = True  # True = descendente (mayor primero)
        self._sorting = False  # selector de orden/filtro abierto
        self._sort_col = 0     # columna (grupo) resaltada en el selector
        self._sort_row = 0     # fila (campo) resaltada en el selector
        self._spec_filter = None  # filtrar por especialidad (Specialty o None = todas)
        self._youth_sel = 0    # prospecto seleccionado en la Cantera
        # --- Estado del Mercado ---
        self._mkt_sel = 0      # listado seleccionado
        self._mkt_search = False
        self._mkt_query = ""
        self._offering = False  # ingresando el monto de una oferta
        self._offer_text = ""   # monto tipeado

    # --- Datos ---
    @property
    def _players(self) -> list:
        game = self.app.game
        if game is None or game.player_club is None:
            return []
        return game.player_club.players

    @property
    def _today(self):
        return self.app.game.calendar.current_date

    def _haystack(self, p) -> str:
        """Todos los valores visibles del jugador + su especialidad completa, para buscar."""
        extra = SPECIALTY_LABEL[p.specialty] if p.specialty else ""
        return " ".join(self._cell_values(p) + [extra]).lower()

    def _filtered_players(self) -> list:
        """Jugadores tras el buscador y el filtro de especialidad (sin ordenar)."""
        players = self._players
        if self._query:
            q = self._query.lower()
            players = [p for p in players if q in self._haystack(p)]
        if self._spec_filter is not None:
            players = [p for p in players if p.specialty is self._spec_filter]
        return players

    def _visible(self) -> list:
        """Jugadores tras buscador + filtro de especialidad + orden (copia, no muta)."""
        players = self._filtered_players()
        if self._sort_key is not None:
            _label, fn = _SORT_BY_ID[self._sort_key]
            players = sorted(players, key=lambda p: fn(p, self._today),
                             reverse=self._sort_desc)
        return players

    def _squad_specialties(self) -> list:
        """Especialidades presentes HOY en el plantel, en orden de enum (dinamico)."""
        present = {p.specialty for p in self._players if p.specialty is not None}
        return [s for s in Specialty if s in present]

    # --- Render por pestaña ---
    def render_tab(self, index: int) -> Text:
        if index == 1:
            return self._youth_text()
        if index == 2:
            return self._market_text()
        return self._table_text()

    # --- Cantera (juveniles que traen los ojeadores; ver simulation/youth.py) ---
    @property
    def _club(self):
        game = self.app.game
        return game.player_club if game else None

    def _youth_text(self) -> Text:
        club = self._club
        if club is None:
            return Text("Sin club todavia.", style="white")
        game = self.app.game
        today = game.calendar.current_date
        prospects = club.prospects
        # Sin Complejo juvenil / sin ojeadores: explicar como habilitar la cantera.
        if not youth.has_academy(club) or not youth.scouts(club):
            return self._youth_empty(club, game, today)
        if not prospects:
            nxt = youth.next_intake(game, today)
            when = nxt.strftime("%d-%m-%Y") if nxt else "la proxima temporada"
            t = Text()
            append_section(t, "CANTERA", [
                (f"Tus {len(youth.scouts(club))} ojeador(es) estan trabajando.", "white"),
                "",
                (f"Proxima camada de juveniles: {when}.", "grey70"),
                ("Cuando lleguen, vas a poder revisar su informe y decidir.", "grey62"),
            ])
            return t

        self._youth_sel = max(0, min(len(prospects) - 1, self._youth_sel))
        t = Text()
        nxt = youth.next_intake(game, today)
        t.append(f"CANTERA   {len(prospects)} juvenil(es)", style="bold green")
        if nxt:
            t.append(f"   Proxima camada {nxt.strftime('%d-%m')}", style="grey62")
        t.append("\n")
        t.append("-" * _WIDTH + "\n", style="grey50")
        left = self._youth_left_lines(prospects, today)
        right = self._youth_detail_lines(prospects[self._youth_sel], club, today)
        rows = 16
        for i in range(rows):
            if i == rows - 1:
                t.append("\n"); continue
            lline = left[i] if i < len(left) else Text("")
            rline = right[i] if i < len(right) else Text("")
            t.append_text(lline)
            t.append(" " * max(0, _YTH_LEFT - len(lline.plain)))
            t.append("| ", style="grey50")
            t.append_text(rline)
            t.append("\n")
        pr = prospects[self._youth_sel]
        if not pr.revealed:
            t.append_text(hint(("^v", "elegir"), ("Enter", "revisar informe"),
                               ("Supr", "descartar")))
        else:
            t.append_text(hint(("^v", "elegir"), ("Enter", "fichar"),
                               ("Supr", "descartar")))
        return t

    def _youth_empty(self, club, game, today) -> Text:
        t = Text()
        has_b = youth.has_academy(club)
        append_section(t, "CANTERA", [
            ("Para descubrir juveniles necesitas:", "white"),
            "",
            (f"  [{'x' if has_b else ' '}] Complejo juvenil "
             f"(Club > Instalaciones)", "green" if has_b else "grey70"),
            (f"  [{'x' if youth.scouts(club) else ' '}] Cazatalentos contratados "
             f"(Club > Empleados)", "green" if youth.scouts(club) else "grey70"),
            "",
            ("Cada ojeador trae un juvenil dos veces por temporada; vos decidis", "grey62"),
            ("si lo incorporas. Son jovenes con techo alto (entrenan rapido).", "grey62"),
        ])
        return t

    def _youth_left_lines(self, prospects, today) -> list:
        lines = [Text("PROSPECTOS", style="bold green")]
        for i, pr in enumerate(prospects):
            p = pr.player
            tag = "visto" if pr.revealed else "nuevo"
            text = f" {p.full_name:<16.16} {p.position.value:<3} {p.age_on(today)}a {tag}"
            if i == self._youth_sel:
                lines.append(Text(text[:_YTH_LEFT].ljust(_YTH_LEFT), style="bold black on green"))
            else:
                lines.append(Text(text[:_YTH_LEFT], style="white" if pr.revealed else "yellow"))
        return lines

    def _youth_detail_lines(self, pr, club, today) -> list:
        p = pr.player
        lines = [Text(f"{p.full_name}", style="bold white"),
                 Text(f"{p.position.value}  {p.age_on(today)} anios  {p.nationality}  "
                      f"pie {FOOT_SHORT[p.foot]}", style="grey70")]
        if not pr.revealed:
            n = youth.reveal_count(pr.scout_skill)
            lines += [
                Text(""),
                Text(f"Informe sin revisar.", style="yellow"),
                Text(f"Ojeador con Ojeo {pr.scout_skill:.0f}: evaluo {n} de "
                     f"{len(ALL_ATTRS)} atributos.", style="grey70"),
                Text(""),
                Text("Enter: revisar el informe (descubrir).", style="bold cyan"),
            ]
            return lines
        # Revelado: potencial, destacado y los atributos evaluados (resto "?").
        shown = set(youth.revealed_attrs(pr))
        standout = youth.standout_attr(pr)
        lines.append(Text(f"Potencial est: {youth.potential_stars(pr)}   "
                          f"Destacado: {ATTR_LABEL[standout]}", style="white"))
        lines.append(Text(""))
        # Grilla de 3 columnas: sigla + valor (o "?" si el ojeador no lo evaluo).
        col_w = _YTH_RIGHT // 3
        for r in range(5):
            line = Text()
            for c in range(3):
                idx = c * 5 + r
                if idx >= len(ALL_ATTRS):
                    line.append(" " * col_w); continue
                attr = ALL_ATTRS[idx]
                val = f"{getattr(p, attr):.0f}" if attr in shown else "?"
                cell = f"{ATTR_SHORT[attr]} {val:>4}".ljust(col_w)
                line.append(cell, style="bold cyan" if attr == standout else
                            ("white" if attr in shown else "grey42"))
            lines.append(line)
        lines.append(Text(""))
        if len(club.players) >= T.MAX_SQUAD:
            lines.append(Text(f"Plantel lleno ({T.MAX_SQUAD}). Vende para fichar.", "grey62"))
        else:
            lines.append(Text("Enter: fichar (gratis)    Supr: descartar", style="green"))
        return lines

    def _key_cantera(self, event) -> None:
        club = self._club
        if club is None:
            return
        prospects = club.prospects
        if not prospects:
            return
        key = event.key
        if key == "up":
            event.stop(); self._youth_sel = max(0, self._youth_sel - 1); self._refresh_content()
        elif key == "down":
            event.stop(); self._youth_sel = min(len(prospects) - 1, self._youth_sel + 1); self._refresh_content()
        elif key == "enter":
            event.stop(); self._youth_action(prospects[self._youth_sel])
        elif key in ("delete", "backspace") or event.character in ("x", "X"):
            event.stop()
            youth.discard(self.app.game, prospects[self._youth_sel])
            self._youth_sel = max(0, self._youth_sel - 1)
            savegame.save_game(self.app.game)
            self._refresh_content()

    def _youth_action(self, pr) -> None:
        """Enter: primero revisa el informe; ya revisado, ficha al juvenil."""
        if not pr.revealed:
            youth.reveal(pr)
        elif youth.sign(self.app.game, pr):
            self._youth_sel = max(0, self._youth_sel - 1)
        savegame.save_game(self.app.game)
        self._refresh_content()

    # --- Mercado (interactivo: listados, ofertas, negociacion) ---
    def _mkt_listings(self) -> list:
        """Listados del mundo (excluye tu club), ordenados por overall y filtrados."""
        game = self.app.game
        club = game.player_club if game else None
        rows = [(p, c) for (p, c) in T.all_listings(game) if c is not club]
        rows.sort(key=lambda pc: pc[0].overall, reverse=True)
        if self._mkt_query:
            q = self._mkt_query.lower()
            rows = [(p, c) for (p, c) in rows
                    if q in p.full_name.lower() or q in p.position.value.lower()
                    or q in c.name.lower()]
        return rows

    def _my_offer(self, player):
        return next((o for o in self.app.game.offers if o.target is player), None)

    def _market_text(self) -> Text:
        game = self.app.game
        if game is None or game.player_club is None:
            return Text("Sin club todavia.", style="white")
        listings = self._mkt_listings()
        total = len(listings)
        pages = max(1, (total + _MKT_PAGE - 1) // _MKT_PAGE)
        self._mkt_sel = max(0, min(total - 1, self._mkt_sel)) if total else 0
        page = self._mkt_sel // _MKT_PAGE if total else 0
        page_rows = listings[page * _MKT_PAGE:page * _MKT_PAGE + _MKT_PAGE]

        t = Text()
        t.append(f"MERCADO   {total} en venta   ", style="bold green")
        t.append(f"Caja {money(game.player_club.capital)}", style="grey70")
        if self._mkt_query:
            t.append(f"   [filtro: {self._mkt_query}]", style="grey62")
        t.append("\n")
        cells = [self._fmt(h, w, a) for h, w, a in _MKT_COLS]
        t.append("  " + " ".join(cells) + "\n", style="bold green")
        t.append("-" * _WIDTH + "\n", style="grey50")
        if total == 0:
            t.append("  No hay jugadores en venta.\n", style="grey62")
            shown = 1
        else:
            for offset, (p, c) in enumerate(page_rows):
                self._mkt_row(t, p, c, page * _MKT_PAGE + offset == self._mkt_sel)
            shown = len(page_rows)
        for _ in range(_MKT_PAGE - shown):
            t.append("\n")
        self._mkt_offers_panel(t)
        self._mkt_footer(t, page + 1, pages, listings)
        return t

    def _mkt_row(self, t: Text, p, club, selected: bool) -> None:
        values = [
            str(p.shirt_number or "-"), p.full_name, p.position.value,
            str(round(p.overall)), str(p.age_on(self._today)),
            money(p.asking_price), club.name,
        ]
        cells = [self._fmt(v, w, a) for v, (_, w, a) in zip(values, _MKT_COLS)]
        if selected:
            t.append(("> " + " ".join(cells)).ljust(_WIDTH) + "\n",
                     style="bold black on green")
            return
        offer = self._my_offer(p)
        name_style = "bold cyan" if offer and offer.open else "white"
        t.append("  ")
        for i, cell in enumerate(cells):
            t.append(cell, style=name_style if i == 1 else "white")
            if i < len(cells) - 1:
                t.append(" ")
        t.append("\n")

    def _mkt_offers_panel(self, t: Text) -> None:
        t.append("MIS OFERTAS\n", style="bold green")
        recent = self.app.game.offers[-3:]
        if not recent:
            t.append("  ninguna\n", style="grey62")
            return
        for o in recent:
            if o.status == PENDING:
                extra, style = "pendiente", "yellow"
            elif o.status == COUNTERED:
                extra, style = f"contraoferta {money(o.counter_amount)} (A aceptar / X quitar)", "bold cyan"
            elif o.status == "accepted":
                extra, style = "aceptada", "green"
            elif o.status == "withdrawn":
                extra, style = "retirada", "grey62"
            else:
                extra, style = "rechazada", "red"
            t.append(f"  {o.target.full_name:.20} {money(o.amount)}  ", style="white")
            t.append(extra + "\n", style=style)

    def _mkt_footer(self, t: Text, page: int, pages: int, listings) -> None:
        if self._mkt_search:
            t.append("Buscar: ", style="bold yellow")
            t.append(self._mkt_query + "_", style="bold white")
            t.append("   ")
            t.append_text(hint(("Enter", "aplicar"), ("Esc", "salir")))
            return
        if self._offering:
            target = listings[self._mkt_sel][0]
            t.append(f"Oferta por {target.full_name:.18}: $", style="bold yellow")
            t.append(self._offer_text + "_", style="bold white")
            t.append("   ")
            t.append_text(hint(("Enter", "ofertar"), ("Esc", "cancelar")))
            return
        t.append_text(hint(("Flechas", "mover"), ("Enter", "ofertar"),
                           ("A", "aceptar"), ("X", "retirar"), ("/", "buscar")))
        t.append(f"   Pag {page}/{pages}", style="grey62")

    @property
    def _page_size(self) -> int:
        """Filas de jugadores visibles (menos cuando el panel de atributos esta abierto)."""
        return _PEEK_PAGE if self._peek else _PAGE_SIZE

    # --- Tabla de la plantilla ---
    def _table_text(self) -> Text:
        club = self.app.game.player_club if self.app.game else None
        if not self._players:
            return Text("No hay jugadores para mostrar.", style="white")
        if self._sorting:
            return self._sort_picker_text()

        visible = self._visible()
        total = len(visible)
        size = self._page_size
        pages = max(1, (total + size - 1) // size)
        self._selected = max(0, min(total - 1, self._selected)) if total else 0
        page = self._selected // size if total else 0
        start = page * size
        page_players = visible[start:start + size]

        t = Text()
        squad = len(self._players)
        filtered = self._query or self._spec_filter is not None
        status = f"{club.name}   "
        status += f"{total}/{squad} jug" if filtered else f"{squad} jugadores"
        status += f"   Orden: {self._sort_desc_text()}"
        if self._spec_filter is not None:
            status += f"   Filtro: {SPECIALTY_LABEL[self._spec_filter]}"
        status += "   "
        t.append(status[:66], style="grey62")   # se acota: el detalle completo esta en [O]
        t.append_text(hint(("O", "filtros")))   # la tecla en amarillo (acento)
        t.append("\n")
        self._append_header(t)
        if total == 0:
            t.append(f"  Sin resultados para \"{self._query}\".\n", style="grey62")
            shown = 1
        else:
            for offset, player in enumerate(page_players):
                self._append_row(t, player, start + offset == self._selected)
            shown = len(page_players)
        for _ in range(size - shown):
            t.append("\n")
        if self._peek and total:                       # vistazo rapido inline
            self._peek_panel(t, visible[self._selected])
        else:
            t.append("\n")  # aire entre la tabla y la ayuda de teclas
        self._append_footer(t, page + 1, pages)
        return t

    def _peek_panel(self, t: Text, p) -> None:
        """Panel inline con los 15 atributos del jugador en foco (sin popup)."""
        t.append("-" * _WIDTH + "\n", style="grey50")
        t.append(f"  {p.full_name}  {p.position.value} {p.age_on(self._today)}a   ",
                 style="bold white")
        t.append(f"OVR {p.overall:.0f}  POT {p.potential:.0f}  "
                 f"FOR {p.form:.0f}  FIT {p.fitness:.0f}\n", style="grey70")
        col_w = 26
        for title, _attrs in ATTR_GROUPS:
            t.append(title.ljust(col_w), style="bold green")
        t.append("\n")
        rows = max(len(attrs) for _t, attrs in ATTR_GROUPS)
        for i in range(rows):
            for _title, attrs in ATTR_GROUPS:
                if i >= len(attrs):
                    t.append(" " * col_w); continue
                attr = attrs[i]
                value = getattr(p, attr)
                cell = (ATTR_LABEL[attr].ljust(13) + f"{value:.1f}".rjust(5)).ljust(col_w)
                t.append(cell, style=_attr_color(value))
            if i < rows - 1:
                t.append("\n")

    # --- Orden de la plantilla (selector en grilla + aplicacion) ---
    def _sort_desc_text(self) -> str:
        """Texto del orden actual para el subtitulo (ej. 'OVR desc' o 'plantel')."""
        if self._sort_key is None:
            return "plantel"
        label, _fn = _SORT_BY_ID[self._sort_key]
        return f"{label} {'desc' if self._sort_desc else 'asc'}"

    def _open_sort(self) -> None:
        """Abre el selector de orden, posicionado sobre el campo actual (si hay)."""
        self._sorting = True
        self._sort_col, self._sort_row = 0, 0
        for ci, (_g, fields) in enumerate(_SORT_GROUPS):
            for ri, (fid, _l, _fn) in enumerate(fields):
                if fid == self._sort_key:
                    self._sort_col, self._sort_row = ci, ri
        self._refresh_content()

    def _picker_field(self):
        """El campo (id, etiqueta, fn) resaltado en el selector."""
        return _SORT_GROUPS[self._sort_col][1][self._sort_row]

    def _spec_filter_text(self) -> str:
        """Etiqueta del filtro de especialidad actual (o 'Todas')."""
        return SPECIALTY_LABEL[self._spec_filter] if self._spec_filter else "Todas"

    def _sort_picker_text(self) -> Text:
        fid, label, fn = self._picker_field()
        t = Text()
        t.append("ORDENAR / FILTRAR", style="bold green")
        t.append(f"   (orden: {self._sort_desc_text()})\n", style="grey62")
        # Filtro por especialidad (dinamico: solo las presentes en el plantel).
        n_spec = len(self._squad_specialties())
        t.append("Filtro especialidad: ", style="grey62")
        t.append(self._spec_filter_text(),
                 style="bold cyan" if self._spec_filter else "white")
        t.append("   ")
        t.append_text(hint(("F", f"cambiar ({n_spec} en el plantel)")))
        t.append("\n")
        t.append("-" * _WIDTH + "\n", style="grey50")
        # --- Grilla de campos (5 columnas) ---
        col_w = _WIDTH // len(_SORT_GROUPS)   # 80 / 5 = 16
        for gtitle, _fields in _SORT_GROUPS:
            t.append(gtitle.ljust(col_w), style="bold green")
        t.append("\n")
        for r in range(max(len(f) for _g, f in _SORT_GROUPS)):
            for ci, (_g, fields) in enumerate(_SORT_GROUPS):
                if r >= len(fields):
                    t.append(" " * col_w); continue
                f2id, f2label, _f2 = fields[r]
                sel = ci == self._sort_col and r == self._sort_row
                text = f" {'>' if sel else ' '}{f2label}"
                if sel:
                    style = "bold black on green"
                elif f2id == self._sort_key:
                    style = "bold cyan"      # el campo por el que se ordena ahora
                else:
                    style = "white"
                t.append(text[:col_w].ljust(col_w), style=style)
            t.append("\n")
        # --- Vista previa en vivo: el plantel (filtrado) rankeado por el campo resaltado ---
        t.append("\n")
        pdesc = (not self._sort_desc) if fid == self._sort_key else (fid not in _SORT_TEXT)
        base = self._filtered_players()
        t.append(f"VISTA PREVIA   {label} {'desc' if pdesc else 'asc'}   "
                 f"({len(base)} jug.)\n", style="bold green")
        ranked = sorted(base, key=lambda p: fn(p, self._today), reverse=pdesc)
        prows = 6
        for i in range(prows):
            line = Text()
            for c in range(2):                # dos columnas de ranking
                idx = c * prows + i
                if idx < len(ranked):
                    self._preview_cell(line, idx + 1, ranked[idx], fid, fn)
                else:
                    line.append(" " * 40)
            t.append_text(line); t.append("\n")
        t.append_text(hint(("Flechas", "mover"), ("Enter", "ordenar (repetir invierte)"),
                           ("F", "filtrar"), ("Esc", "cerrar")))
        return t

    def _preview_cell(self, line: Text, rank: int, p, fid: str, fn) -> None:
        """Una celda del ranking de la vista previa: 'N. Nombre   valor'."""
        val = fn(p, self._today)
        if fid == "name":
            disp = ""                          # el nombre ya se muestra
        elif isinstance(val, float):
            disp = f"{val:.1f}"
        else:
            disp = str(val)
        line.append(f" {rank:>2}. ", style="grey50")   # 5
        line.append(f"{p.full_name:<24.24}", style="white")  # 24
        line.append(f" {disp:>6}", style=_attr_color(val) if isinstance(val, float) else "grey70")  # 7
        line.append(" " * 4)                    # relleno hasta 40 por columna (5+24+7+4)

    def _key_sorting(self, event) -> None:
        key = event.key
        fields = _SORT_GROUPS[self._sort_col][1]
        if key == "up":
            event.stop(); self._sort_row = max(0, self._sort_row - 1); self._refresh_content()
        elif key == "down":
            event.stop(); self._sort_row = min(len(fields) - 1, self._sort_row + 1); self._refresh_content()
        elif key == "left":
            event.stop(); self._sort_col = max(0, self._sort_col - 1)
            self._sort_row = min(self._sort_row, len(_SORT_GROUPS[self._sort_col][1]) - 1)
            self._refresh_content()
        elif key == "right":
            event.stop(); self._sort_col = min(len(_SORT_GROUPS) - 1, self._sort_col + 1)
            self._sort_row = min(self._sort_row, len(_SORT_GROUPS[self._sort_col][1]) - 1)
            self._refresh_content()
        elif event.character in ("f", "F"):
            event.stop(); self._cycle_spec_filter(); self._refresh_content()
        elif key == "enter":
            event.stop(); self._apply_sort()
        elif key == "escape":
            event.stop(); self._sorting = False; self._refresh_content()

    def _cycle_spec_filter(self) -> None:
        """Cicla el filtro de especialidad: Todas -> cada especialidad presente -> Todas."""
        options = [None] + self._squad_specialties()   # dinamico segun el plantel
        try:
            i = options.index(self._spec_filter)
        except ValueError:
            i = 0                                       # el filtro actual ya no esta presente
        self._spec_filter = options[(i + 1) % len(options)]
        self._selected = 0

    def _apply_sort(self) -> None:
        """Aplica el campo resaltado. Si ya era el activo, invierte el sentido."""
        fid, _label, _fn = _SORT_GROUPS[self._sort_col][1][self._sort_row]
        if self._sort_key == fid:
            self._sort_desc = not self._sort_desc          # mismo campo -> invertir
        else:
            self._sort_key = fid
            self._sort_desc = fid not in _SORT_TEXT        # numerico desc, texto asc
        self._sorting = False
        self._selected = 0
        self._refresh_content()

    def _append_footer(self, t: Text, page: int, pages: int) -> None:
        if self._searching:
            t.append("Buscar: ", style="bold yellow")
            t.append(self._query + "_", style="bold white")
            t.append("   ")
            t.append_text(hint(("Enter", "ficha"), ("Esc", "cancelar")))
        elif self._compare_from is not None:
            # Modo comparar: barra propia (elegir el 2do jugador o cancelar).
            t.append(f"Comparar con {self._compare_from.full_name:.16}: ",
                     style="bold cyan")
            t.append_text(hint(("Enter", "2do jugador"), ("Esc", "cancelar")))
        elif self._releasing is not None:
            # Confirmacion del despido (o aviso si el plantel esta en el minimo).
            if T.can_release(self.app.game.player_club):
                t.append(f"Despedir a {self._releasing.full_name:.20}? ", style="bold red")
                t.append_text(hint(("Enter", "si"), ("Esc", "no")))
            else:
                t.append(f"Plantel en el minimo ({T.MIN_ROSTER}). No podes despedir. ",
                         style="bold yellow")
                t.append_text(hint(("Esc", "volver")))
        else:
            # El estado (lesion/sancion/venta) ya se lee en la columna EST y en el
            # color del nombre; aca solo van los atajos.
            peek = "ocultar" if self._peek else "atributos"
            t.append_text(hint(
                ("Enter", "ficha"), ("A", peek), ("M", "comp"),
                ("V", "vender"), ("D", "desp"), ("/", "buscar"), sep="  ",
            ))
        t.append(f"  Pag {page}/{pages}", style="grey62")

    @staticmethod
    def _fmt(text, width: int, align: str) -> str:
        text = str(text)[:width]
        return text.rjust(width) if align == "r" else text.ljust(width)

    def _append_header(self, t: Text) -> None:
        cells = [self._fmt(h, w, a) for h, w, a in _COLUMNS]
        line = ("  " + " ".join(cells)).ljust(_WIDTH)
        t.append(line + "\n", style="bold green")
        t.append("-" * _WIDTH + "\n", style="grey50")

    def _append_row(self, t: Text, p, selected: bool) -> None:
        values = self._cell_values(p)
        cells = [self._fmt(v, w, a) for v, (_, w, a) in zip(values, _COLUMNS)]
        if selected:
            line = ("> " + " ".join(cells)).ljust(_WIDTH)
            t.append(line + "\n", style="bold black on green")
            return
        marked = p is self._compare_from  # A de la comparacion (no en foco)
        t.append("A " if marked else "  ", style="bold cyan" if marked else "white")
        for i, cell in enumerate(cells):
            if marked and i == 1:
                style = "bold cyan"     # nombre en cyan = marcado para comparar
            elif i == 1 and p.asking_price is not None:
                style = "bold yellow"   # nombre en amarillo = esta en venta
            elif i == _MOR_IDX:
                style = _MORALE_STYLE.get(int(cell), "white")
            elif i == _ESP_IDX:
                style = "grey42" if cell.strip() == "-" else "bold cyan"
            elif i == _EST_IDX:
                v = cell.strip()
                style = "grey42" if v == "-" else "yellow" if v == "1A" else "bold red"
            else:
                style = "white"
            t.append(cell, style=style)
            if i < len(cells) - 1:
                t.append(" ")
        used = 2 + sum(len(c) for c in cells) + (len(cells) - 1)
        if used < _WIDTH:
            t.append(" " * (_WIDTH - used))
        t.append("\n")

    def _cell_values(self, p) -> list:
        esp = SPECIALTY_SHORT[p.specialty] if p.specialty else "-"
        return [
            str(p.shirt_number or "-"),
            p.full_name,
            p.position.value,
            p.nationality,
            str(p.age_on(self._today)),
            FOOT_SHORT[p.foot],
            str(round(p.overall)),
            str(round(p.potential)),
            str(round(p.form)),
            str(round(p.fitness)),
            str(p.morale.value),
            esp,
            self._est_value(p),
        ]

    def _est_value(self, p) -> str:
        """Marcador de estado: lesion (con semanas), suspension o amarilla."""
        if p.injury is not None:
            return f"L{p.injury_weeks_left(self._today)}"
        if p.matches_suspended > 0:
            return "SUS"
        if p.yellow_cards >= 1:
            return "1A"
        return "-"

    # --- Interaccion (solo en la pestaña Plantilla) ---
    def _open_detail(self) -> None:
        visible = self._visible()
        if not visible:
            return
        from .player_detail_screen import PlayerDetailScreen

        self.app.push_screen(
            PlayerDetailScreen(visible, self._selected, self._today, self._on_detail_close)
        )

    def _on_detail_close(self, index: int) -> None:
        self._selected = index
        self._refresh_content()

    def _move(self, delta: int) -> None:
        total = len(self._visible())
        if total:
            self._selected = max(0, min(total - 1, self._selected + delta))
        self._refresh_content()

    def content_captures_keys(self) -> bool:
        # Con un buscador, el input de oferta o el selector de orden/filtro abiertos, la
        # pestaña consume TODO el teclado (para escribir/usar letras como 'F' sin que el
        # marco cambie de seccion/pestaña).
        return ((self._active_tab == _PLANTILLA and (self._searching or self._sorting))
                or (self._active_tab == _MERCADO and (self._mkt_search or self._offering)))

    def on_content_key(self, event) -> None:
        if self._active_tab == _CANTERA:
            self._key_cantera(event)
            return
        if self._active_tab == _PLANTILLA:
            self._key_plantilla(event)
        elif self._active_tab == _MERCADO:
            self._key_market(event)

    def _key_plantilla(self, event) -> None:
        if not self._players:
            return
        if self._searching:
            self._on_key_search(event, event.key)
            return
        if self._releasing is not None:      # modal: confirmar/cancelar el despido
            self._key_releasing(event)
            return
        if self._sorting:                    # modal: selector de orden
            self._key_sorting(event)
            return
        key = event.key
        comparing = self._compare_from is not None
        if key == "up":
            event.stop(); self._move(-1)
        elif key == "down":
            event.stop(); self._move(1)
        elif key in ("left", "pageup"):
            event.stop(); self._move(-self._page_size)
        elif key in ("right", "pagedown"):
            event.stop(); self._move(self._page_size)
        elif event.character == "a":
            event.stop(); self._peek = not self._peek; self._refresh_content()
        elif event.character == "o" and not comparing:
            event.stop(); self._open_sort()
        elif event.character == "m":
            event.stop(); self._toggle_compare_mark()
        elif comparing and key == "escape":
            event.stop(); self._compare_from = None; self._refresh_content()
        elif comparing and key == "enter":
            event.stop(); self._open_compare()
        elif key == "enter":
            event.stop(); self._open_detail()
        elif event.character == "v" and not comparing:  # bloqueado mientras se compara
            event.stop(); self._toggle_sale()
        elif event.character == "d" and not comparing:  # despedir (con confirmacion)
            event.stop()
            visible = self._visible()
            if visible:
                self._releasing = visible[self._selected]
                self._refresh_content()
        elif event.character == "/":
            self._searching = True
            self._query = ""
            self._selected = 0
            event.stop(); self._refresh_content()

    def _key_releasing(self, event) -> None:
        """Confirmacion del despido: Enter rescinde (si no baja de 11), Esc cancela."""
        key = event.key
        if key == "enter":
            event.stop()
            club = self.app.game.player_club
            if T.release_player(club, self._releasing):
                self._selected = max(0, self._selected - 1)
                savegame.save_game(self.app.game)
            self._releasing = None
            self._refresh_content()
        elif key == "escape":
            event.stop(); self._releasing = None; self._refresh_content()
        else:
            event.stop()  # modal: el resto de las teclas no hacen nada

    def _toggle_compare_mark(self) -> None:
        """Marca (o desmarca) al jugador en foco como A para comparar."""
        visible = self._visible()
        if not visible:
            return
        focused = visible[self._selected]
        self._compare_from = None if focused is self._compare_from else focused
        self._refresh_content()

    def _open_compare(self) -> None:
        """Abre la comparacion entre A (marcado) y B (en foco)."""
        visible = self._visible()
        if not visible:
            return
        b = visible[self._selected]
        if b is self._compare_from:  # no comparar a un jugador consigo mismo
            return
        from .compare_players_screen import ComparePlayersScreen

        self.app.push_screen(
            ComparePlayersScreen(self._compare_from, b, self._today,
                                 self._on_compare_close)
        )

    def _on_compare_close(self) -> None:
        self._compare_from = None
        self._refresh_content()

    def _toggle_sale(self) -> None:
        visible = self._visible()
        if not visible:
            return
        player = visible[self._selected]
        if player.asking_price is not None:
            T.unlist_player(player)
        elif len(self._players) > T.MIN_SQUAD:  # no vender por debajo del minimo
            T.list_player(player, today=self._today)
        self._refresh_content()

    # --- Teclado del Mercado ---
    def _key_market(self, event) -> None:
        if self._offering:
            self._key_offering(event)
            return
        if self._mkt_search:
            self._key_mkt_search(event)
            return
        key = event.key
        listings = self._mkt_listings()
        if key == "up":
            event.stop(); self._mkt_sel = max(0, self._mkt_sel - 1); self._refresh_content()
        elif key == "down":
            event.stop(); self._mkt_sel = min(len(listings) - 1, self._mkt_sel + 1); self._refresh_content()
        elif key in ("left", "pageup"):
            event.stop(); self._mkt_sel = max(0, self._mkt_sel - _MKT_PAGE); self._refresh_content()
        elif key in ("right", "pagedown"):
            event.stop(); self._mkt_sel = min(len(listings) - 1, self._mkt_sel + _MKT_PAGE); self._refresh_content()
        elif key == "enter" and listings:
            event.stop()
            self._offering = True
            self._offer_text = str(listings[self._mkt_sel][0].asking_price)
            self._refresh_content()
        elif event.character == "a" and listings:  # aceptar contraoferta
            event.stop()
            offer = self._my_offer(listings[self._mkt_sel][0])
            if offer and offer.status == COUNTERED:
                T.accept_counter(self.app.game, offer)
            self._refresh_content()
        elif event.character == "x" and listings:  # retirar oferta
            event.stop()
            offer = self._my_offer(listings[self._mkt_sel][0])
            if offer and offer.open:
                T.withdraw_offer(offer)
            self._refresh_content()
        elif event.character == "/":
            event.stop()
            self._mkt_search = True; self._mkt_query = ""; self._mkt_sel = 0
            self._refresh_content()

    def _key_offering(self, event) -> None:
        key = event.key
        if key == "escape":
            event.stop(); self._offering = False; self._refresh_content()
        elif key == "enter":
            event.stop()
            listings = self._mkt_listings()
            amount = int(self._offer_text) if self._offer_text.isdigit() else 0
            if listings and amount > 0:
                T.make_offer(self.app.game, listings[self._mkt_sel][0], amount)
            self._offering = False
            self._refresh_content()
        elif key == "backspace":
            event.stop(); self._offer_text = self._offer_text[:-1]; self._refresh_content()
        elif event.character and event.character.isdigit():
            event.stop(); self._offer_text += event.character; self._refresh_content()

    def _key_mkt_search(self, event) -> None:
        key = event.key
        if key in ("escape", "enter"):
            event.stop(); self._mkt_search = False; self._refresh_content()
        elif key == "backspace":
            event.stop(); self._mkt_query = self._mkt_query[:-1]; self._mkt_sel = 0; self._refresh_content()
        elif event.character and event.character.isprintable() and len(event.character) == 1:
            event.stop(); self._mkt_query += event.character; self._mkt_sel = 0; self._refresh_content()

    def _on_key_search(self, event, key: str) -> None:
        if key == "escape":
            self._searching = False
            self._query = ""
            self._selected = 0
            event.stop(); self._refresh_content()
        elif key == "enter":
            event.stop(); self._open_detail()
        elif key == "backspace":
            self._query = self._query[:-1]
            self._selected = 0
            event.stop(); self._refresh_content()
        elif key in ("up", "down", "left", "right", "pageup", "pagedown"):
            step = {"up": -1, "down": 1, "left": -_PAGE_SIZE, "right": _PAGE_SIZE,
                    "pageup": -_PAGE_SIZE, "pagedown": _PAGE_SIZE}[key]
            event.stop(); self._move(step)
        elif event.character and event.character.isprintable() and len(event.character) == 1:
            self._query += event.character
            self._selected = 0
            event.stop(); self._refresh_content()
