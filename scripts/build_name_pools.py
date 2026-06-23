"""Destila el dataset de nombres (~10GB) en pools compactos por pais.

Lee datasets/names/data/<CODIGO>.csv y escribe, por cada pais que usa el juego,
tacticore/generators/data/names/<CODIGO>.json con la forma:

    {"first": [...nombres...], "last": [...apellidos...]}

con los mas frecuentes, normalizados a ASCII (directiva 2). Esos JSON son
chicos y SI se commitean: el juego corre sin el dataset de 10GB. Los nombres se
combinan mezclando first + last (no se reproducen personas reales).

Es tooling de desarrollo: se corre una vez (o cuando se agregan paises).

    python scripts/build_name_pools.py

El dataset grande NO esta versionado. Para regenerar los JSON hay que bajarlo
y dejar los CSV por pais en datasets/names/data/ (ver README, seccion "Nombres
por nacionalidad"). Descarga:
https://drive.google.com/file/d/1QDbtPWGQypYxiS4pC_hHBBtbRHk9gEtr/view?usp=sharing
"""

import csv
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "datasets" / "names" / "data"
OUT = ROOT / "tacticore" / "generators" / "data" / "names"

MAX_ROWS = 400_000   # filas a leer por pais (muestra suficiente para frecuencias)
TOP_N = 800          # cuantos nombres / apellidos guardar por pais
_NAME_RE = re.compile(r"[A-Za-z][A-Za-z .'-]*$")


def asciify(text: str) -> str:
    """Pasa a ASCII sin acentos (lo que no se puede mapear, se descarta)."""
    norm = unicodedata.normalize("NFKD", text)
    return norm.encode("ascii", "ignore").decode("ascii").strip()


def is_valid(name: str) -> bool:
    """Acepta nombres ASCII razonables (letras, espacio, guion, apostrofe)."""
    return 2 <= len(name) <= 20 and bool(_NAME_RE.match(name))


def distill(code: str) -> dict | None:
    """Devuelve {'first': [...], 'last': [...]} para un pais, o None."""
    path = SRC / f"{code}.csv"
    if not path.exists():
        return None
    first: Counter = Counter()
    last: Counter = Counter()
    with path.open(encoding="utf-8", errors="ignore", newline="") as fh:
        reader = csv.reader(fh)
        for i, row in enumerate(reader):
            if i >= MAX_ROWS:
                break
            if len(row) < 4:
                continue
            fn, ln, gender = asciify(row[0]), asciify(row[1]), row[2]
            # Nombres de pila: solo varones (jugadores de futbol).
            if gender == "M" and is_valid(fn):
                first[fn] += 1
            if is_valid(ln):
                last[ln] += 1
    return {
        "first": [n for n, _ in first.most_common(TOP_N)],
        "last": [n for n, _ in last.most_common(TOP_N)],
    }


def main() -> None:
    sys.path.insert(0, str(ROOT))
    from tacticore.generators.data.country_data import COUNTRIES

    OUT.mkdir(parents=True, exist_ok=True)
    for name, code in COUNTRIES:
        data = distill(code)
        if not data or len(data["first"]) < 20 or len(data["last"]) < 20:
            n_first = len(data["first"]) if data else 0
            n_last = len(data["last"]) if data else 0
            print(f"  {code} {name}: POCOS ({n_first}/{n_last}) -> se omite (usa fallback)")
            continue
        (OUT / f"{code}.json").write_text(
            json.dumps(data, ensure_ascii=True), encoding="utf-8"
        )
        print(f"  {code} {name}: first={len(data['first'])} last={len(data['last'])}")


if __name__ == "__main__":
    main()
