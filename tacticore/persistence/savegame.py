"""Guardado y carga del estado de la partida (SQLite, stdlib).

Cada partida es un archivo `.sqlite` en `config.SAVE_DIR`. Por ahora hay una sola
ranura (autosave): `savegame.sqlite`. El formato en disco es relacional (ver
`_db.py`); en memoria seguimos usando el grafo de dataclasses (`GameState`).
"""

import sqlite3
from pathlib import Path

from .. import config
from ..core.game import GameState
from . import _db

_DEFAULT_NAME = "savegame.sqlite"


def default_save_path() -> Path:
    """Ruta del autosave unico."""
    return config.SAVE_DIR / _DEFAULT_NAME


def save_exists(path: Path | None = None) -> bool:
    """Indica si hay un archivo de partida guardada."""
    return (path or default_save_path()).exists()


def compatible_save_exists(path: Path | None = None) -> bool:
    """True si hay un save y su schema coincide con el actual (se puede cargar).

    Un save de una version vieja (ej. antes de que existieran los directores
    tecnicos) NO es compatible: se ignora para arrancar una partida nueva en vez
    de romper al intentar leerlo.
    """
    path = path or default_save_path()
    if not path.exists():
        return False
    try:
        conn = sqlite3.connect(path)
        try:
            row = conn.execute("SELECT schema_version FROM meta").fetchone()
        finally:
            conn.close()
    except sqlite3.Error:
        return False
    return bool(row) and row[0] == _db.SCHEMA_VERSION


def save_game(state: GameState, path: Path | None = None) -> None:
    """Guarda la partida en disco (reescribe el archivo entero)."""
    path = path or default_save_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    try:
        _db.write_game(conn, state)
    finally:
        conn.close()


def load_game(path: Path | None = None) -> GameState:
    """Carga una partida guardada y devuelve su `GameState`."""
    path = path or default_save_path()
    conn = sqlite3.connect(path)
    try:
        return _db.read_game(conn)
    finally:
        conn.close()
