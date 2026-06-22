"""Carga de los pools de nombres por pais (destilados del dataset real).

Los JSON viven en data/names/<CODIGO>.json y se generan con
scripts/build_name_pools.py. Se cargan bajo demanda y se cachean. Si un pais no
tiene pool, devuelve None y el generador usa su fallback silabico.
"""

import json
from functools import lru_cache
from pathlib import Path

_NAMES_DIR = Path(__file__).resolve().parent / "data" / "names"


@lru_cache(maxsize=None)
def load_pool(country_code: str) -> tuple[list[str], list[str]] | None:
    """Devuelve (nombres, apellidos) del pais, o None si no hay pool."""
    path = _NAMES_DIR / f"{country_code}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["first"], data["last"]
