"""Esquema SQLite y conversores fila <-> dataclass para el guardado.

Detalle interno de `savegame.py`. El save es el grafo del juego volcado a tablas
relacionales: countries -> leagues -> clubs -> players. El estadio y el manager
van inline en la fila del club (hoy son 1:1, asi evitamos joins). Los enums se
guardan por su `.value` y las fechas en ISO (`YYYY-MM-DD`).
"""

import sqlite3
from datetime import date

from ..core.calendar import GameCalendar
from ..core.game import GameState
from ..domain.club import Club
from ..domain.coach import Coach
from ..domain.country import Country
from ..domain.enums import Foot, LeagueTier, Mentality, Morale, Position, Specialty
from ..domain.league import League
from ..domain.manager import Manager
from ..domain.player import ALL_ATTRS, Player
from ..domain.stadium import Stadium

# v3: cada club guarda su director tecnico (coach_*) inline en la fila del club.
SCHEMA_VERSION = 3


class IncompatibleSaveError(Exception):
    """El save es de una version de schema distinta a la actual (no se puede leer)."""

# Columnas de jugador, separadas para construirlas una sola vez (DRY con ALL_ATTRS).
_PLAYER_BASE_COLS = [
    "first_name", "last_name", "nationality", "position", "foot", "birth_date",
    "height_cm", "weight_kg", "form", "fitness", "experience", "morale",
    "specialty", "nickname", "shirt_number", "origin_club", "potential",
    "injury_proneness",
]
_PLAYER_COLS = _PLAYER_BASE_COLS + list(ALL_ATTRS)

# DDL. Los atributos del jugador (ALL_ATTRS) son columnas REAL generadas aca.
_PLAYER_ATTR_DDL = ",\n    ".join(f"{attr} REAL NOT NULL" for attr in ALL_ATTRS)

SCHEMA = f"""
PRAGMA foreign_keys = ON;

CREATE TABLE meta (
    schema_version INTEGER NOT NULL,
    seed           INTEGER NOT NULL,
    current_date   TEXT NOT NULL,
    manager_name   TEXT NOT NULL,
    player_club_id INTEGER
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
    stadium_capacity INTEGER NOT NULL,
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
    coach_leadership REAL
);

CREATE TABLE players (
    id        INTEGER PRIMARY KEY,
    club_id   INTEGER NOT NULL REFERENCES clubs(id),
    first_name       TEXT NOT NULL,
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
    {_PLAYER_ATTR_DDL}
);

-- Lesiones (activas + historial). Arranca vacia; se poblara con la simulacion.
CREATE TABLE injuries (
    id              INTEGER PRIMARY KEY,
    player_id       INTEGER NOT NULL REFERENCES players(id),
    type            TEXT NOT NULL,
    severity        INTEGER NOT NULL,
    start_date      TEXT NOT NULL,
    expected_return TEXT NOT NULL,
    is_active       INTEGER NOT NULL
);

-- Indices en las FK: sin esto, cargar el mundo escanea tablas enteras por cada
-- club/liga (la carga pasaba de ~16s a <1s con estos indices).
CREATE INDEX idx_leagues_country ON leagues(country_id);
CREATE INDEX idx_clubs_league    ON clubs(league_id);
CREATE INDEX idx_players_club    ON players(club_id);
CREATE INDEX idx_injuries_player ON injuries(player_id);
"""


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
                if is_player:
                    player_club_id = club_id
                _insert_players(conn, club_id, club.players)

    conn.execute(
        "INSERT INTO meta (schema_version, seed, current_date, manager_name, "
        "player_club_id) VALUES (?, ?, ?, ?, ?)",
        (
            SCHEMA_VERSION,
            game.seed,
            game.calendar.current_date.isoformat(),
            game.manager_name,
            player_club_id,
        ),
    )
    conn.commit()


def _insert_club(
    conn: sqlite3.Connection, league_id: int, club: Club, is_player: bool
) -> int:
    mgr = club.manager
    coach = club.coach
    return conn.execute(
        """
        INSERT INTO clubs (
            league_id, name, short_name, country_code, tier, capital, members,
            fans_name, is_player_club, stadium_name, stadium_capacity,
            manager_first, manager_last, manager_nat, manager_birth,
            coach_first, coach_last, coach_nat, coach_birth,
            coach_mentality, coach_skill, coach_leadership
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            league_id, club.name, club.short_name, club.country_code,
            club.tier.value, club.capital, club.members, club.fans_name,
            int(is_player), club.stadium.name, club.stadium.capacity,
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
        ),
    ).lastrowid


def _insert_players(
    conn: sqlite3.Connection, club_id: int, players: list[Player]
) -> None:
    placeholders = ", ".join(["?"] * (1 + len(_PLAYER_COLS)))
    columns = "club_id, " + ", ".join(_PLAYER_COLS)
    rows = [_player_row(club_id, player) for player in players]
    conn.executemany(
        f"INSERT INTO players ({columns}) VALUES ({placeholders})", rows
    )


def _player_row(club_id: int, p: Player) -> tuple:
    base = (
        p.first_name, p.last_name, p.nationality, p.position.value, p.foot.value,
        p.birth_date.isoformat(), p.height_cm, p.weight_kg, p.form, p.fitness,
        p.experience, p.morale.value, p.specialty.value if p.specialty else None,
        p.nickname, p.shirt_number, p.origin_club, p.potential, p.injury_proneness,
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
                league.clubs.append(club)
                if clrow["id"] == meta["player_club_id"]:
                    player_club = club
            country.leagues.append(league)
        countries.append(country)

    return GameState(
        seed=meta["seed"],
        calendar=GameCalendar(current_date=date.fromisoformat(meta["current_date"])),
        countries=countries,
        player_club=player_club,
        manager_name=meta["manager_name"],
    )


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
    return Club(
        name=row["name"],
        short_name=row["short_name"],
        country_code=row["country_code"],
        tier=LeagueTier(row["tier"]),
        stadium=Stadium(name=row["stadium_name"], capacity=row["stadium_capacity"]),
        capital=row["capital"],
        members=row["members"],
        fans_name=row["fans_name"],
        manager=manager,
        players=players,
        coach=coach,
    )


def _player_from_row(row: sqlite3.Row) -> Player:
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
        **{attr: row[attr] for attr in ALL_ATTRS},
    )
