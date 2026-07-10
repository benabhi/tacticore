"""Esquema SQLite y conversores fila <-> dataclass para el guardado.

Detalle interno de `savegame.py`. El save es el grafo del juego volcado a tablas
relacionales: countries -> leagues -> clubs -> players. El estadio y el manager
van inline en la fila del club (hoy son 1:1, asi evitamos joins). Los enums se
guardan por su `.value` y las fechas en ISO (`YYYY-MM-DD`).
"""

import json
import sqlite3
from datetime import date

from ..core.calendar import GameCalendar
from ..core.game import GameState
from ..domain.club import Club
from ..domain.coach import Coach
from ..domain.country import Country
from ..domain.employee import Employee
from ..domain.enums import (
    BonusType, EmployeeRole, Foot, InjurySeverity, InjuryType, LeagueTier, Mentality,
    MatchKind, Morale, Position, Specialty)
from ..domain.facility import Construction
from ..domain.injury import Injury
from ..domain.league import League
from ..domain.manager import Manager
from ..domain.match import Match
from ..domain.movement import Movement
from ..domain.notification import Notification
from ..domain.player import ALL_ATTRS, Player
from ..domain.prospect import Prospect
from ..domain.sponsor import Sponsor, SponsorContract
from ..domain.stadium import Stadium
from ..domain.transfer import TransferOffer

# v15: entrenamiento por atributo (players.training_focus).
# v14: empleados con multiples bonus (employees.bonuses JSON en vez de skill).
# v13: eventos accionables (notifications kind/payload/status) + patrocinadores
# multiples (club.sponsors, cupos por tier).
# v12: numero de temporada en meta (ascensos/descensos al cerrar la temporada).
# v11: cuerpo de trabajo (tabla employees: medico, director financiero, ...). v10:
# lesion activa + tarjetas/suspension por jugador (se quita la tabla injuries
# huerfana). v9: notificaciones, amistosos y libro de caja; v8 entrenamiento de
# formaciones; v7 liderazgo/caracter; v6 mercado; v5 instalaciones; v4 estadio por
# sectores + patrocinadores; v3 el DT.
SCHEMA_VERSION = 16   # v16: cantera (prospectos de juveniles por ojeador)


class IncompatibleSaveError(Exception):
    """El save es de una version de schema distinta a la actual (no se puede leer)."""

# Columnas de jugador, separadas para construirlas una sola vez (DRY con ALL_ATTRS).
_PLAYER_BASE_COLS = [
    "first_name", "last_name", "nationality", "position", "foot", "birth_date",
    "height_cm", "weight_kg", "form", "fitness", "experience", "morale",
    "specialty", "nickname", "shirt_number", "origin_club", "potential",
    "injury_proneness", "asking_price", "leadership", "character",
    "yellow_cards", "matches_suspended",
    "injury_type", "injury_severity", "injury_start", "injury_return",
    "training_focus",
]
_PLAYER_COLS = _PLAYER_BASE_COLS + list(ALL_ATTRS)

# DDL. Los atributos del jugador (ALL_ATTRS) son columnas REAL generadas aca.
_PLAYER_ATTR_DDL = ",\n    ".join(f"{attr} REAL NOT NULL" for attr in ALL_ATTRS)

# Columnas de un jugador (sin id/club_id), compartidas por las tablas `players` y
# `prospects` (los juveniles de la cantera son Players a la espera de decision).
# Compartir el DDL garantiza paridad de columnas -> `_player_from_row` sirve para
# ambas tablas.
_PLAYER_COLS_DDL = f"""    first_name       TEXT NOT NULL,
    last_name        TEXT NOT NULL,
    nationality      TEXT NOT NULL,
    position         TEXT NOT NULL,
    foot             TEXT NOT NULL,
    birth_date       TEXT NOT NULL,
    height_cm        INTEGER NOT NULL,
    weight_kg        INTEGER NOT NULL,
    form             REAL NOT NULL,
    fitness          REAL NOT NULL,
    experience       REAL NOT NULL,
    morale           INTEGER NOT NULL,
    specialty        TEXT,
    nickname         TEXT,
    shirt_number     INTEGER,
    origin_club      TEXT,
    potential        REAL NOT NULL,
    injury_proneness REAL NOT NULL,
    asking_price     INTEGER,
    leadership       INTEGER NOT NULL DEFAULT 3,
    character        INTEGER NOT NULL DEFAULT 3,
    yellow_cards       INTEGER NOT NULL DEFAULT 0,
    matches_suspended  INTEGER NOT NULL DEFAULT 0,
    injury_type        TEXT,
    injury_severity    INTEGER,
    injury_start       TEXT,
    injury_return      TEXT,
    training_focus     TEXT,
    {_PLAYER_ATTR_DDL}"""

SCHEMA = f"""
PRAGMA foreign_keys = ON;

CREATE TABLE meta (
    schema_version INTEGER NOT NULL,
    seed           INTEGER NOT NULL,
    current_date   TEXT NOT NULL,
    manager_name   TEXT NOT NULL,
    player_club_id INTEGER,
    season         INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE countries (
    id   INTEGER PRIMARY KEY,
    code TEXT NOT NULL,
    name TEXT NOT NULL
);

CREATE TABLE leagues (
    id         INTEGER PRIMARY KEY,
    country_id INTEGER NOT NULL REFERENCES countries(id),
    tier       TEXT NOT NULL,
    name       TEXT NOT NULL
);

CREATE TABLE clubs (
    id               INTEGER PRIMARY KEY,
    league_id        INTEGER NOT NULL REFERENCES leagues(id),
    name             TEXT NOT NULL,
    short_name       TEXT NOT NULL,
    country_code     TEXT NOT NULL,
    tier             TEXT NOT NULL,
    capital          INTEGER NOT NULL,
    members          INTEGER NOT NULL,
    fans_name        TEXT NOT NULL,
    is_player_club   INTEGER NOT NULL DEFAULT 0,
    stadium_name     TEXT NOT NULL,
    stadium_general    INTEGER NOT NULL,
    stadium_preferente INTEGER NOT NULL,
    stadium_tribuna    INTEGER NOT NULL,
    stadium_palco      INTEGER NOT NULL,
    manager_first    TEXT,
    manager_last     TEXT,
    manager_nat      TEXT,
    manager_birth    TEXT,
    coach_first      TEXT,
    coach_last       TEXT,
    coach_nat        TEXT,
    coach_birth      TEXT,
    coach_mentality  TEXT,
    coach_skill      REAL,
    coach_leadership REAL,
    plots            INTEGER NOT NULL DEFAULT 0,
    stands_built     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE players (
    id        INTEGER PRIMARY KEY,
    club_id   INTEGER NOT NULL REFERENCES clubs(id),
{_PLAYER_COLS_DDL}
);

-- Prospectos de la cantera: juveniles que trajo un ojeador, a la espera de
-- decision. Reusan las columnas de jugador + metadatos del ojeo. Solo el club del
-- jugador tiene filas.
CREATE TABLE prospects (
    id          INTEGER PRIMARY KEY,
    club_id     INTEGER NOT NULL REFERENCES clubs(id),
    scout_skill REAL NOT NULL,
    revealed    INTEGER NOT NULL,
    found_date  TEXT NOT NULL,
    expires     TEXT NOT NULL,
{_PLAYER_COLS_DDL}
);

-- Patrocinador principal de cada club (0 o 1 por club, tabla aparte).
CREATE TABLE sponsors (
    id               INTEGER PRIMARY KEY,
    club_id          INTEGER NOT NULL REFERENCES clubs(id),
    name             TEXT NOT NULL,
    sector           TEXT NOT NULL,
    tier             INTEGER NOT NULL,
    weeks_total      INTEGER NOT NULL,
    weeks_remaining  INTEGER NOT NULL,
    weekly_pay       INTEGER NOT NULL,
    signing_bonus    INTEGER NOT NULL,
    promotion_bonus  INTEGER NOT NULL,
    streak_bonus     INTEGER NOT NULL,
    streak_len       INTEGER NOT NULL
);

-- Instalaciones construidas de cada club (id del edificio -> nivel).
CREATE TABLE facilities (
    id          INTEGER PRIMARY KEY,
    club_id     INTEGER NOT NULL REFERENCES clubs(id),
    facility_id TEXT NOT NULL,
    level       INTEGER NOT NULL
);

-- Cuerpo de trabajo de cada club (medico, director financiero, ...). Variable por
-- club; hoy solo el club del jugador tiene empleados.
CREATE TABLE employees (
    id          INTEGER PRIMARY KEY,
    club_id     INTEGER NOT NULL REFERENCES clubs(id),
    role        TEXT NOT NULL,
    first_name  TEXT NOT NULL,
    last_name   TEXT NOT NULL,
    nationality TEXT NOT NULL,
    birth_date  TEXT,
    bonuses     TEXT NOT NULL,
    weekly_wage INTEGER NOT NULL
);

-- Obras en curso de cada club (bajan un dia por vez en el loop diario).
CREATE TABLE constructions (
    id             INTEGER PRIMARY KEY,
    club_id        INTEGER NOT NULL REFERENCES clubs(id),
    kind           TEXT NOT NULL,
    key            TEXT NOT NULL,
    days_remaining INTEGER NOT NULL
);

-- Entrenamiento de formaciones por club (nombre de formacion -> nivel 1-100).
-- Hoy solo el club del jugador tiene filas.
CREATE TABLE formation_training (
    id        INTEGER PRIMARY KEY,
    club_id   INTEGER NOT NULL REFERENCES clubs(id),
    formation TEXT NOT NULL,
    level     REAL NOT NULL
);

-- Ofertas abiertas del jugador humano (el comprador es siempre su club). El
-- objetivo se reconecta por el club vendedor + numero de camiseta.
CREATE TABLE offers (
    id             INTEGER PRIMARY KEY,
    seller_club_id INTEGER NOT NULL REFERENCES clubs(id),
    player_shirt   INTEGER NOT NULL,
    amount         INTEGER NOT NULL,
    status         TEXT NOT NULL,
    counter_amount INTEGER NOT NULL,
    days_left      INTEGER NOT NULL
);

-- Partidos del fixture de cada liga (con su resultado si ya se jugaron). La
-- tactica del club del jugador NO se persiste (es transitoria).
CREATE TABLE matches (
    id           INTEGER PRIMARY KEY,
    league_id    INTEGER NOT NULL REFERENCES leagues(id),
    matchday     INTEGER NOT NULL,
    home_club_id INTEGER NOT NULL REFERENCES clubs(id),
    away_club_id INTEGER NOT NULL REFERENCES clubs(id),
    kind         TEXT NOT NULL,
    match_date   TEXT,
    home_goals   INTEGER NOT NULL,
    away_goals   INTEGER NOT NULL,
    played       INTEGER NOT NULL
);

-- Notificaciones (registro de novedades para el manager). Orden = orden de id.
CREATE TABLE notifications (
    id       INTEGER PRIMARY KEY,
    subject  TEXT NOT NULL,
    message  TEXT NOT NULL,
    date     TEXT NOT NULL,
    category TEXT NOT NULL,
    read     INTEGER NOT NULL,
    kind     TEXT NOT NULL DEFAULT '',
    payload  TEXT,
    status   TEXT NOT NULL DEFAULT ''
);

-- Libro de caja del club del jugador (movimientos en tiempo real). Orden = id.
CREATE TABLE movements (
    id      INTEGER PRIMARY KEY,
    club_id INTEGER NOT NULL REFERENCES clubs(id),
    date    TEXT NOT NULL,
    concept TEXT NOT NULL,
    amount  INTEGER NOT NULL
);

-- Amistosos del club del jugador (miercoles), guardados aparte de la liga.
CREATE TABLE friendlies (
    id           INTEGER PRIMARY KEY,
    matchday     INTEGER NOT NULL,
    home_club_id INTEGER NOT NULL REFERENCES clubs(id),
    away_club_id INTEGER NOT NULL REFERENCES clubs(id),
    kind         TEXT NOT NULL,
    match_date   TEXT,
    home_goals   INTEGER NOT NULL,
    away_goals   INTEGER NOT NULL,
    played       INTEGER NOT NULL
);

-- Indices en las FK: sin esto, cargar el mundo escanea tablas enteras por cada
-- club/liga (la carga pasaba de ~16s a <1s con estos indices).
CREATE INDEX idx_leagues_country ON leagues(country_id);
CREATE INDEX idx_clubs_league    ON clubs(league_id);
CREATE INDEX idx_players_club       ON players(club_id);
CREATE INDEX idx_sponsors_club      ON sponsors(club_id);
CREATE INDEX idx_employees_club     ON employees(club_id);
CREATE INDEX idx_facilities_club    ON facilities(club_id);
CREATE INDEX idx_constructions_club ON constructions(club_id);
CREATE INDEX idx_ftrain_club        ON formation_training(club_id);
CREATE INDEX idx_matches_league     ON matches(league_id);
CREATE INDEX idx_movements_club     ON movements(club_id);
"""

# Estados de oferta que se persisten (solo las abiertas; las cerradas son historia).
_OPEN_OFFER_STATUS = ("pending", "countered")


def _iso(value: date | None) -> str | None:
    """Fecha a ISO, o None."""
    return value.isoformat() if value is not None else None


def _date(value: str | None) -> date | None:
    """ISO a fecha, o None."""
    return date.fromisoformat(value) if value else None


# --------------------------------------------------------------------------- #
# Escritura
# --------------------------------------------------------------------------- #
def write_game(conn: sqlite3.Connection, game: GameState) -> None:
    """Crea el esquema y vuelca el `GameState` entero en una transaccion."""
    conn.executescript(SCHEMA)
    player_club_id: int | None = None
    club_ids: dict[int, int] = {}  # id(objeto Club) -> club_id en la base

    for country in game.countries:
        country_id = conn.execute(
            "INSERT INTO countries (code, name) VALUES (?, ?)",
            (country.code, country.name),
        ).lastrowid
        for league in country.leagues:
            league_id = conn.execute(
                "INSERT INTO leagues (country_id, tier, name) VALUES (?, ?, ?)",
                (country_id, league.tier.value, league.name),
            ).lastrowid
            for club in league.clubs:
                is_player = club is game.player_club
                club_id = _insert_club(conn, league_id, club, is_player)
                club_ids[id(club)] = club_id
                if is_player:
                    player_club_id = club_id
                _insert_players(conn, club_id, club.players)
                _insert_prospects(conn, club_id, club.prospects)
            _insert_matches(conn, league_id, league.matches, club_ids)

    _insert_offers(conn, game, club_ids)
    _insert_friendlies(conn, game, club_ids)
    _insert_notifications(conn, game)
    conn.execute(
        "INSERT INTO meta (schema_version, seed, current_date, manager_name, "
        "player_club_id, season) VALUES (?, ?, ?, ?, ?, ?)",
        (
            SCHEMA_VERSION,
            game.seed,
            game.calendar.current_date.isoformat(),
            game.manager_name,
            player_club_id,
            game.season,
        ),
    )
    conn.commit()


def _insert_club(
    conn: sqlite3.Connection, league_id: int, club: Club, is_player: bool
) -> int:
    mgr = club.manager
    coach = club.coach
    st = club.stadium
    club_id = conn.execute(
        """
        INSERT INTO clubs (
            league_id, name, short_name, country_code, tier, capital, members,
            fans_name, is_player_club, stadium_name,
            stadium_general, stadium_preferente, stadium_tribuna, stadium_palco,
            manager_first, manager_last, manager_nat, manager_birth,
            coach_first, coach_last, coach_nat, coach_birth,
            coach_mentality, coach_skill, coach_leadership,
            plots, stands_built
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            league_id, club.name, club.short_name, club.country_code,
            club.tier.value, club.capital, club.members, club.fans_name,
            int(is_player), st.name,
            st.general, st.preferente, st.tribuna, st.palco,
            mgr.first_name if mgr else None,
            mgr.last_name if mgr else None,
            mgr.nationality if mgr else None,
            _iso(mgr.birth_date) if mgr else None,
            coach.first_name if coach else None,
            coach.last_name if coach else None,
            coach.nationality if coach else None,
            _iso(coach.birth_date) if coach else None,
            coach.mentality.value if coach else None,
            coach.skill if coach else None,
            coach.leadership if coach else None,
            club.plots, club.stands_built,
        ),
    ).lastrowid
    _insert_sponsors(conn, club_id, club)
    _insert_employees(conn, club_id, club)
    _insert_facilities(conn, club_id, club)
    _insert_movements(conn, club_id, club)
    return club_id


def _insert_employees(conn: sqlite3.Connection, club_id: int, club: Club) -> None:
    """Guarda el cuerpo de trabajo del club (medico, director financiero, ...)."""
    rows = [
        (club_id, e.role.value, e.first_name, e.last_name, e.nationality,
         _iso(e.birth_date), json.dumps({t.value: v for t, v in e.bonuses.items()}),
         e.weekly_wage)
        for e in club.employees
    ]
    if rows:
        conn.executemany(
            """
            INSERT INTO employees (
                club_id, role, first_name, last_name, nationality, birth_date,
                bonuses, weekly_wage
            ) VALUES (?,?,?,?,?,?,?,?)
            """,
            rows,
        )


def _insert_movements(conn: sqlite3.Connection, club_id: int, club: Club) -> None:
    """Guarda el libro de caja del club (solo el del jugador suele tener filas)."""
    rows = [(club_id, _iso(mv.date), mv.concept, mv.amount) for mv in club.movements]
    if rows:
        conn.executemany(
            "INSERT INTO movements (club_id, date, concept, amount) VALUES (?,?,?,?)",
            rows)


def _insert_facilities(conn: sqlite3.Connection, club_id: int, club: Club) -> None:
    """Guarda instalaciones, obras y entrenamiento de formaciones del club."""
    facs = [(club_id, fid, lv) for fid, lv in club.facilities.items() if lv > 0]
    if facs:
        conn.executemany(
            "INSERT INTO facilities (club_id, facility_id, level) VALUES (?,?,?)", facs)
    cons = [(club_id, c.kind, c.key, c.days_remaining) for c in club.constructions]
    if cons:
        conn.executemany(
            "INSERT INTO constructions (club_id, kind, key, days_remaining) "
            "VALUES (?,?,?,?)", cons)
    ftrain = [(club_id, name, lv) for name, lv in club.formation_training.items()]
    if ftrain:
        conn.executemany(
            "INSERT INTO formation_training (club_id, formation, level) "
            "VALUES (?,?,?)", ftrain)


def _insert_sponsors(conn: sqlite3.Connection, club_id: int, club: Club) -> None:
    """Guarda los contratos de patrocinio del club (0..N, cupos por tier)."""
    rows = [
        (club_id, c.sponsor.name, c.sponsor.sector, c.sponsor.tier, c.weeks_total,
         c.weeks_remaining, c.weekly_pay, c.signing_bonus, c.promotion_bonus,
         c.streak_bonus, c.streak_len)
        for c in club.sponsors
    ]
    if rows:
        conn.executemany(
            """
            INSERT INTO sponsors (
                club_id, name, sector, tier, weeks_total, weeks_remaining, weekly_pay,
                signing_bonus, promotion_bonus, streak_bonus, streak_len
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            rows,
        )


def _insert_matches(
    conn: sqlite3.Connection, league_id: int, matches: list, club_ids: dict[int, int]
) -> None:
    """Guarda los partidos del fixture de una liga (resultado incluido)."""
    if not matches:
        return
    rows = [
        (
            league_id, m.matchday, club_ids[id(m.home)], club_ids[id(m.away)],
            m.kind.value, _iso(m.match_date), m.home_goals, m.away_goals, int(m.played),
        )
        for m in matches
    ]
    conn.executemany(
        """
        INSERT INTO matches (
            league_id, matchday, home_club_id, away_club_id, kind, match_date,
            home_goals, away_goals, played
        ) VALUES (?,?,?,?,?,?,?,?,?)
        """,
        rows,
    )


def _owner_of(game: GameState, player: Player) -> Club | None:
    for country in game.countries:
        for league in country.leagues:
            for club in league.clubs:
                if player in club.players:
                    return club
    return None


def _insert_offers(
    conn: sqlite3.Connection, game: GameState, club_ids: dict[int, int]
) -> None:
    """Guarda las ofertas ABIERTAS del jugador (por club vendedor + camiseta)."""
    rows = []
    for o in game.offers:
        if o.status not in _OPEN_OFFER_STATUS:
            continue
        seller = _owner_of(game, o.target)
        if seller is None or o.target.shirt_number is None:
            continue
        rows.append((club_ids[id(seller)], o.target.shirt_number, o.amount,
                     o.status, o.counter_amount, o.days_left))
    if rows:
        conn.executemany(
            "INSERT INTO offers (seller_club_id, player_shirt, amount, status, "
            "counter_amount, days_left) VALUES (?,?,?,?,?,?)", rows)


def _insert_friendlies(
    conn: sqlite3.Connection, game: GameState, club_ids: dict[int, int]
) -> None:
    """Guarda los amistosos del jugador (con su resultado si ya se jugaron)."""
    rows = [
        (
            m.matchday, club_ids[id(m.home)], club_ids[id(m.away)], m.kind.value,
            _iso(m.match_date), m.home_goals, m.away_goals, int(m.played),
        )
        for m in game.friendlies
    ]
    if rows:
        conn.executemany(
            """
            INSERT INTO friendlies (
                matchday, home_club_id, away_club_id, kind, match_date,
                home_goals, away_goals, played
            ) VALUES (?,?,?,?,?,?,?,?)
            """,
            rows,
        )


def _insert_notifications(conn: sqlite3.Connection, game: GameState) -> None:
    """Guarda el registro de notificaciones (en orden de llegada)."""
    rows = [
        (n.subject, n.message, _iso(n.date), n.category, int(n.read),
         n.kind, json.dumps(n.payload) if n.payload is not None else None, n.status)
        for n in game.notifications
    ]
    if rows:
        conn.executemany(
            "INSERT INTO notifications (subject, message, date, category, read, "
            "kind, payload, status) VALUES (?,?,?,?,?,?,?,?)", rows)


def _insert_players(
    conn: sqlite3.Connection, club_id: int, players: list[Player]
) -> None:
    placeholders = ", ".join(["?"] * (1 + len(_PLAYER_COLS)))
    columns = "club_id, " + ", ".join(_PLAYER_COLS)
    rows = [_player_row(club_id, player) for player in players]
    conn.executemany(
        f"INSERT INTO players ({columns}) VALUES ({placeholders})", rows
    )


def _insert_prospects(conn: sqlite3.Connection, club_id: int, prospects: list) -> None:
    """Vuelca los prospectos de la cantera (metadatos del ojeo + columnas de jugador)."""
    if not prospects:
        return
    meta_cols = ["scout_skill", "revealed", "found_date", "expires"]
    columns = "club_id, " + ", ".join(meta_cols + _PLAYER_COLS)
    placeholders = ", ".join(["?"] * (1 + len(meta_cols) + len(_PLAYER_COLS)))
    rows = []
    for pr in prospects:
        meta = (pr.scout_skill, 1 if pr.revealed else 0,
                pr.found_date.isoformat(), pr.expires.isoformat())
        rows.append((club_id, *meta, *_player_row(club_id, pr.player)[1:]))
    conn.executemany(
        f"INSERT INTO prospects ({columns}) VALUES ({placeholders})", rows)


def _player_row(club_id: int, p: Player) -> tuple:
    inj = p.injury
    base = (
        p.first_name, p.last_name, p.nationality, p.position.value, p.foot.value,
        p.birth_date.isoformat(), p.height_cm, p.weight_kg, p.form, p.fitness,
        p.experience, p.morale.value, p.specialty.value if p.specialty else None,
        p.nickname, p.shirt_number, p.origin_club, p.potential, p.injury_proneness,
        p.asking_price, p.leadership, p.character,
        p.yellow_cards, p.matches_suspended,
        inj.type.value if inj else None, inj.severity.value if inj else None,
        _iso(inj.start_date) if inj else None,
        _iso(inj.expected_return) if inj else None,
        p.training_focus,
    )
    attrs = tuple(getattr(p, attr) for attr in ALL_ATTRS)
    return (club_id, *base, *attrs)


# --------------------------------------------------------------------------- #
# Lectura
# --------------------------------------------------------------------------- #
def read_game(conn: sqlite3.Connection) -> GameState:
    """Reconstruye el `GameState` completo desde la base."""
    conn.row_factory = sqlite3.Row
    meta = conn.execute("SELECT * FROM meta").fetchone()
    if meta["schema_version"] != SCHEMA_VERSION:
        raise IncompatibleSaveError(meta["schema_version"], SCHEMA_VERSION)

    countries: list[Country] = []
    player_club: Club | None = None
    club_by_id: dict[int, Club] = {}  # club_id en la base -> objeto Club
    for crow in conn.execute("SELECT * FROM countries ORDER BY id"):
        country = Country(name=crow["name"], code=crow["code"])
        for lrow in conn.execute(
            "SELECT * FROM leagues WHERE country_id = ? ORDER BY id", (crow["id"],)
        ):
            league = League(
                name=lrow["name"],
                tier=LeagueTier(lrow["tier"]),
                country_code=crow["code"],
            )
            for clrow in conn.execute(
                "SELECT * FROM clubs WHERE league_id = ? ORDER BY id", (lrow["id"],)
            ):
                club = _club_from_row(conn, clrow)
                club_by_id[clrow["id"]] = club
                league.clubs.append(club)
                if clrow["id"] == meta["player_club_id"]:
                    player_club = club
            league.matches = _matches_for_league(conn, lrow["id"], club_by_id)
            country.leagues.append(league)
        countries.append(country)

    return GameState(
        seed=meta["seed"],
        calendar=GameCalendar(current_date=date.fromisoformat(meta["current_date"])),
        countries=countries,
        season=meta["season"],
        player_club=player_club,
        manager_name=meta["manager_name"],
        offers=_offers_from_db(conn, club_by_id),
        friendlies=_friendlies_from_db(conn, club_by_id),
        notifications=_notifications_from_db(conn),
    )


def _friendlies_from_db(
    conn: sqlite3.Connection, club_by_id: dict[int, Club]
) -> list[Match]:
    """Reconstruye los amistosos del jugador, reconectando local/visitante."""
    out: list[Match] = []
    for m in conn.execute("SELECT * FROM friendlies ORDER BY matchday, id"):
        home = club_by_id.get(m["home_club_id"])
        away = club_by_id.get(m["away_club_id"])
        if home is None or away is None:
            continue
        out.append(Match(
            home=home, away=away, matchday=m["matchday"],
            kind=MatchKind(m["kind"]), match_date=_date(m["match_date"]),
            home_goals=m["home_goals"], away_goals=m["away_goals"],
            played=bool(m["played"]),
        ))
    return out


def _notifications_from_db(conn: sqlite3.Connection) -> list[Notification]:
    """Reconstruye el registro de notificaciones (en orden de id)."""
    return [
        Notification(
            subject=r["subject"], message=r["message"],
            date=date.fromisoformat(r["date"]), category=r["category"],
            read=bool(r["read"]), kind=r["kind"],
            payload=json.loads(r["payload"]) if r["payload"] is not None else None,
            status=r["status"],
        )
        for r in conn.execute("SELECT * FROM notifications ORDER BY id")
    ]


def _offers_from_db(
    conn: sqlite3.Connection, club_by_id: dict[int, Club]
) -> list[TransferOffer]:
    """Reconecta las ofertas abiertas (por club vendedor + numero de camiseta)."""
    out: list[TransferOffer] = []
    for r in conn.execute("SELECT * FROM offers"):
        seller = club_by_id.get(r["seller_club_id"])
        if seller is None:
            continue
        target = next((p for p in seller.players
                       if p.shirt_number == r["player_shirt"]), None)
        if target is None:
            continue
        out.append(TransferOffer(
            target=target, amount=r["amount"], status=r["status"],
            counter_amount=r["counter_amount"], days_left=r["days_left"]))
    return out


def _club_from_row(conn: sqlite3.Connection, row: sqlite3.Row) -> Club:
    manager = None
    if row["manager_first"] is not None:
        manager = Manager(
            first_name=row["manager_first"],
            last_name=row["manager_last"],
            nationality=row["manager_nat"],
            birth_date=_date(row["manager_birth"]),
        )
    coach = None
    if row["coach_first"] is not None:
        coach = Coach(
            first_name=row["coach_first"],
            last_name=row["coach_last"],
            nationality=row["coach_nat"],
            birth_date=_date(row["coach_birth"]),
            mentality=Mentality(row["coach_mentality"]),
            skill=row["coach_skill"],
            leadership=row["coach_leadership"],
        )
    players = [
        _player_from_row(prow)
        for prow in conn.execute(
            "SELECT * FROM players WHERE club_id = ? ORDER BY shirt_number", (row["id"],)
        )
    ]
    stadium = Stadium(
        name=row["stadium_name"],
        general=row["stadium_general"],
        preferente=row["stadium_preferente"],
        tribuna=row["stadium_tribuna"],
        palco=row["stadium_palco"],
    )
    return Club(
        name=row["name"],
        short_name=row["short_name"],
        country_code=row["country_code"],
        tier=LeagueTier(row["tier"]),
        stadium=stadium,
        capital=row["capital"],
        members=row["members"],
        fans_name=row["fans_name"],
        manager=manager,
        players=players,
        coach=coach,
        employees=_employees_from_db(conn, row["id"]),
        sponsors=_sponsors_from_db(conn, row["id"]),
        plots=row["plots"],
        stands_built=row["stands_built"],
        facilities={
            f["facility_id"]: f["level"]
            for f in conn.execute(
                "SELECT * FROM facilities WHERE club_id = ?", (row["id"],))
        },
        constructions=[
            Construction(c["kind"], c["key"], c["days_remaining"])
            for c in conn.execute(
                "SELECT * FROM constructions WHERE club_id = ? ORDER BY id", (row["id"],))
        ],
        formation_training={
            f["formation"]: f["level"]
            for f in conn.execute(
                "SELECT * FROM formation_training WHERE club_id = ?", (row["id"],))
        },
        movements=[
            Movement(date=_date(mv["date"]), concept=mv["concept"], amount=mv["amount"])
            for mv in conn.execute(
                "SELECT * FROM movements WHERE club_id = ? ORDER BY id", (row["id"],))
        ],
        prospects=_prospects_from_db(conn, row["id"]),
    )


def _prospects_from_db(conn: sqlite3.Connection, club_id: int) -> list:
    """Reconstruye los prospectos de la cantera (jugador + metadatos del ojeo)."""
    out = []
    for pr in conn.execute(
        "SELECT * FROM prospects WHERE club_id = ? ORDER BY id", (club_id,)
    ):
        out.append(Prospect(
            player=_player_from_row(pr),
            scout_skill=pr["scout_skill"],
            found_date=_date(pr["found_date"]),
            expires=_date(pr["expires"]),
            revealed=bool(pr["revealed"]),
        ))
    return out


def _matches_for_league(
    conn: sqlite3.Connection, league_id: int, club_by_id: dict[int, Club]
) -> list[Match]:
    """Reconstruye los partidos de una liga, reconectando local/visitante."""
    out: list[Match] = []
    for m in conn.execute(
        "SELECT * FROM matches WHERE league_id = ? ORDER BY matchday, id", (league_id,)
    ):
        out.append(Match(
            home=club_by_id[m["home_club_id"]],
            away=club_by_id[m["away_club_id"]],
            matchday=m["matchday"],
            kind=MatchKind(m["kind"]),
            match_date=_date(m["match_date"]),
            home_goals=m["home_goals"],
            away_goals=m["away_goals"],
            played=bool(m["played"]),
        ))
    return out


def _employees_from_db(conn: sqlite3.Connection, club_id: int) -> list[Employee]:
    """Reconstruye el cuerpo de trabajo del club (medico, director financiero, ...)."""
    return [
        Employee(
            role=EmployeeRole(e["role"]),
            first_name=e["first_name"],
            last_name=e["last_name"],
            nationality=e["nationality"],
            birth_date=_date(e["birth_date"]),
            bonuses={BonusType(k): v for k, v in json.loads(e["bonuses"]).items()},
            weekly_wage=e["weekly_wage"],
        )
        for e in conn.execute(
            "SELECT * FROM employees WHERE club_id = ? ORDER BY id", (club_id,))
    ]


def _sponsors_from_db(conn: sqlite3.Connection, club_id: int) -> list[SponsorContract]:
    """Reconstruye los contratos de patrocinio del club (0..N)."""
    return [
        SponsorContract(
            sponsor=Sponsor(name=r["name"], sector=r["sector"], tier=r["tier"]),
            weeks_total=r["weeks_total"], weeks_remaining=r["weeks_remaining"],
            weekly_pay=r["weekly_pay"], signing_bonus=r["signing_bonus"],
            promotion_bonus=r["promotion_bonus"], streak_bonus=r["streak_bonus"],
            streak_len=r["streak_len"],
        )
        for r in conn.execute(
            "SELECT * FROM sponsors WHERE club_id = ? ORDER BY id", (club_id,))
    ]


def _player_from_row(row: sqlite3.Row) -> Player:
    injury = None
    if row["injury_type"] is not None:
        injury = Injury(
            type=InjuryType(row["injury_type"]),
            severity=InjurySeverity(row["injury_severity"]),
            start_date=_date(row["injury_start"]),
            expected_return=_date(row["injury_return"]),
        )
    return Player(
        first_name=row["first_name"],
        last_name=row["last_name"],
        nationality=row["nationality"],
        position=Position(row["position"]),
        foot=Foot(row["foot"]),
        birth_date=date.fromisoformat(row["birth_date"]),
        height_cm=row["height_cm"],
        weight_kg=row["weight_kg"],
        form=row["form"],
        fitness=row["fitness"],
        experience=row["experience"],
        morale=Morale(row["morale"]),
        specialty=Specialty(row["specialty"]) if row["specialty"] else None,
        nickname=row["nickname"],
        shirt_number=row["shirt_number"],
        origin_club=row["origin_club"],
        potential=row["potential"],
        injury_proneness=row["injury_proneness"],
        asking_price=row["asking_price"],
        leadership=row["leadership"],
        character=row["character"],
        yellow_cards=row["yellow_cards"],
        matches_suspended=row["matches_suspended"],
        injury=injury,
        training_focus=row["training_focus"],
        **{attr: row[attr] for attr in ALL_ATTRS},
    )
