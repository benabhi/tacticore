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
GENDER_ROWS = 200_000  # filas por pais para el lexico global de genero (converge antes)
TOP_N = 800          # cuantos nombres / apellidos guardar por pais
_NAME_RE = re.compile(r"[A-Za-z][A-Za-z .'-]*$")

# Tokens que NO son nombres reales: abreviaturas, iniciales, titulos, marcadores
# del dataset. Se descartan (van en minuscula; el chequeo es case-insensitive).
_JUNK = {
    "md", "mohd", "muhd", "mhd", "muhmd", "mohmd", "muhd.", "abo", "abu.",
    "jh", "hj", "mr", "mrs", "ms", "dr", "sr", "jr",
    "male", "female", "na", "nil", "none", "null", "test", "unknown", "user",
}


# Letras que NFKD NO descompone a su base ASCII (no son acento + letra). Sin
# este mapeo se perderian al pasar a ASCII y dejarian fragmentos: p. ej. la "i
# sin punto" turca "Sila" -> "Sla" (que ademas es femenino), "Kiran" -> "Kran".
_TRANSLIT = str.maketrans({
    "ı": "i", "İ": "I",        # i sin punto / I con punto (turco)
    "ł": "l", "Ł": "L",        # l con barra (polaco)
    "ø": "o", "Ø": "O",        # o con barra (nordico)
    "ð": "d", "Ð": "D",        # eth (islandes)
    "þ": "th", "Þ": "Th",      # thorn (islandes)
    "ß": "ss",                      # eszett (aleman)
    "æ": "ae", "Æ": "Ae",      # ae
    "œ": "oe", "Œ": "Oe",      # oe
    "đ": "d", "Đ": "D",        # d con barra (croata/serbio)
    "ħ": "h", "Ħ": "H",        # h con barra (maltes)
})


def asciify(text: str) -> str:
    """Pasa a ASCII sin acentos (lo que no se puede mapear, se descarta)."""
    norm = unicodedata.normalize("NFKD", text.translate(_TRANSLIT))
    return norm.encode("ascii", "ignore").decode("ascii").strip()


def is_valid(name: str, minlen: int = 2) -> bool:
    """Acepta nombres ASCII razonables (letras, espacio, guion, apostrofe).

    `minlen` es la longitud minima: 3 para nombres (evita iniciales/fragmentos
    como 'Sk', 'Ka'), 2 para apellidos (preserva legitimos como 'Ng', 'Ho').
    """
    if not (minlen <= len(name) <= 20 and _NAME_RE.match(name)):
        return False
    return name.lower() not in _JUNK


def _rows(code: str, limit: int):
    """Itera (nombre, apellido, genero) asciificados de un CSV de pais."""
    path = SRC / f"{code}.csv"
    if not path.exists():
        return
    with path.open(encoding="utf-8", errors="ignore", newline="") as fh:
        for i, row in enumerate(csv.reader(fh)):
            if i >= limit:
                break
            if len(row) < 4:
                continue
            yield asciify(row[0]), asciify(row[1]), row[2].strip()


def build_gender_lexicon(pools: list[str]) -> tuple[Counter, Counter]:
    """Cuenta, sobre TODOS los pools, cuantas veces cada nombre va M y F.

    Sirve para los paises SIN columna de genero (p. ej. Turquia): un nombre que
    en el resto del mundo es claramente femenino se descarta de ese pool.
    """
    g_male: Counter = Counter()
    g_female: Counter = Counter()
    for code in pools:
        for fn, _ln, gender in _rows(code, GENDER_ROWS):
            if not is_valid(fn, 3):
                continue
            if gender == "M":
                g_male[fn] += 1
            elif gender == "F":
                g_female[fn] += 1
    return g_male, g_female


def distill(code: str, g_male: Counter, g_female: Counter) -> dict | None:
    """Devuelve {'first': [...], 'last': [...]} para un pais, o None."""
    path = SRC / f"{code}.csv"
    if not path.exists():
        return None
    first_m: Counter = Counter()    # veces que el nombre va etiquetado M en el pais
    first_f: Counter = Counter()    # veces que va etiquetado F en el pais
    first_any: Counter = Counter()  # todas las apariciones (con o sin genero)
    last: Counter = Counter()
    for fn, ln, gender in _rows(code, MAX_ROWS):
        if is_valid(fn, 3):
            first_any[fn] += 1
            if gender == "M":
                first_m[fn] += 1
            elif gender == "F":
                first_f[fn] += 1
        if is_valid(ln, 2):
            last[ln] += 1
    # Si el pais trae genero, nos quedamos con los nombres de MAYORIA masculina
    # LOCAL (mas M que F en ese pais): descarta femeninos mal etiquetados (Monika
    # en Polonia) y respeta convenciones locales (Andrea es masculino en Italia).
    # Si el pais no trae genero (Turquia), filtramos por el lexico global.
    if len(first_m) >= 50:
        first = Counter({
            n: first_m[n] for n in first_m if first_m[n] > first_f[n]
        })
    else:
        first = Counter({
            n: c for n, c in first_any.items()
            if not (g_female[n] > g_male[n] and g_female[n] >= 3)
        })
    return {
        "first": [n for n, _ in first.most_common(TOP_N)],
        "last": [n for n, _ in last.most_common(TOP_N)],
    }


def main() -> None:
    sys.path.insert(0, str(ROOT))
    from tacticore.generators.data.country_data import COUNTRIES, pool_code

    OUT.mkdir(parents=True, exist_ok=True)
    # Un JSON por POOL unico (varios paises pueden compartir pool via NAME_POOL).
    pools = sorted({pool_code(code) for _name, code in COUNTRIES})
    print(f"Construyendo lexico global de genero sobre {len(pools)} pools...")
    g_male, g_female = build_gender_lexicon(pools)
    keep: set[str] = set()
    for code in pools:
        data = distill(code, g_male, g_female)
        if not data or len(data["first"]) < 20 or len(data["last"]) < 20:
            n_first = len(data["first"]) if data else 0
            n_last = len(data["last"]) if data else 0
            print(f"  {code}: POCOS ({n_first}/{n_last}) -> se omite (usa fallback silabico)")
            continue
        (OUT / f"{code}.json").write_text(
            json.dumps(data, ensure_ascii=True), encoding="utf-8"
        )
        keep.add(code)
        print(f"  {code}: first={len(data['first'])} last={len(data['last'])}")

    # Limpia JSON huerfanos (pools que ya no usa ningun pais).
    for old in OUT.glob("*.json"):
        if old.stem not in keep:
            old.unlink()
            print(f"  (borrado huerfano: {old.name})")


if __name__ == "__main__":
    main()
