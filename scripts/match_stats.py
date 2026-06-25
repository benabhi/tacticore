"""Analisis estadistico del motor de partido (herramienta de desarrollo).

Corre N partidos deterministas y junta un conjunto serio de estadisticas para
medir que tan realista esta quedando el motor:

  - Tabla de eventos por partido (remates, cabezazos, faltas, offsides, tiros
    libres, atajadas, corners, laterales, ...) comparada con valores tipicos de
    un partido real (90 min, ambos equipos).
  - Heatmap ASCII de por donde anda la pelota (que zonas se usan mas/menos).
  - Toques de pelota por POSICION (que roles tocan mas la pelota) y posesion.
  - Distribucion de la distancia de remate (cuantos desde adentro del area).

Un "partido" del motor son 600 s simulados (= un partido completo), asi que los
totales por partido se comparan directo con los de un partido real de 90 min.

Uso (con el venv activado):

    python scripts/match_stats.py            # 24 partidos al azar
    python scripts/match_stats.py 50         # 50 partidos
    python scripts/match_stats.py 50 12345   # 50 partidos arrancando en la semilla 12345

Es una herramienta de analisis, no parte del juego.
"""

import sys
from collections import Counter, defaultdict
from pathlib import Path

# Permite ejecutar el script directo (agrega la raiz del repo al path).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tacticore.core.rng import new_rng
from tacticore.domain.enums import LeagueTier
from tacticore.generators import ClubGenerator
from tacticore.simulation.match import (
    FORMATIONS_11,
    MatchEngine,
    Side,
    kickoff_state,
)
from tacticore.simulation.match import ai

_COUNTRIES = ["AR", "BR", "ES", "IT", "FR", "DE", "GB", "NL", "PT", "UY"]
_FULL_TIME = 600.0

# Valores tipicos de un partido real de 90 min (ambos equipos sumados), redondeados.
# Fuente: promedios de ligas top (orden de magnitud, para tener una referencia).
_REAL = {
    "Remates (total)": 25.0,
    "Remates al arco": 9.0,
    "Goles": 2.7,
    "Atajadas": 6.0,
    "Corners": 10.0,
    "Faltas": 22.0,
    "Offsides": 4.0,
    "Laterales": 42.0,
    "Pases": 900.0,
    "Posesion local %": 50.0,
}

# Grilla del heatmap (ancho x alto en celdas). La cancha es 105 x 68 (x, y).
_HM_COLS = 52
_HM_ROWS = 17
_SHADES = " .,:;-=+*xX#%@"  # de menos a mas uso (solo ASCII, directiva 2)


def _build_match(seed: int):
    """Arma dos clubes y formaciones de forma reproducible por seed."""
    setup = new_rng(seed)
    hc, ac = setup.sample(_COUNTRIES, 2)
    tier = setup.choice(list(LeagueTier))
    gen = ClubGenerator(setup)
    home = gen.generate(squad_size=16, country_code=hc, tier=tier)
    away = gen.generate(squad_size=16, country_code=ac, tier=tier)
    hf = setup.choice(FORMATIONS_11)
    af = setup.choice(FORMATIONS_11)
    return home, away, hf, af


def _run_match(seed: int, acc: dict) -> None:
    """Corre un partido y acumula estadisticas en `acc` (in place)."""
    home, away, hf, af = _build_match(seed)
    st = kickoff_state(home, away, home_formation=hf, away_formation=af)
    eng = MatchEngine(st, new_rng(seed))

    heat = acc["heat"]
    touches = acc["touches"]          # rol -> cantidad de toques
    poss = acc["poss"]                # "home"/"away" -> ticks con la pelota
    last_owner = None

    while st.clock < _FULL_TIME:
        eng.step()
        ball = st.ball

        # Heatmap: a donde esta la pelota este tick.
        col = int(ball.position.x / st.pitch.length * (_HM_COLS - 1))
        row = int(ball.position.y / st.pitch.width * (_HM_ROWS - 1))
        col = min(max(col, 0), _HM_COLS - 1)
        row = min(max(row, 0), _HM_ROWS - 1)
        heat[row][col] += 1

        # Posesion y toques por rol: un toque = cuando cambia el dueno de la pelota.
        owner = ball.owner
        if owner is not None:
            poss[owner.team] += 1
            if owner is not last_owner:
                touches[owner.role.value] += 1
        last_owner = owner

    # Eventos del partido (sumados al acumulador, y guardados para promedio/desvio).
    kinds = Counter(e.kind for e in st.log)
    for k, v in kinds.items():
        acc["events"][k] += v
    acc["scores"].append(st.score_home + st.score_away)
    # Distancia de cada remate (para ver cuantos desde adentro del area).
    for d in acc["_shot_dists_this"]:
        acc["shot_dists"].append(d)
    acc["_shot_dists_this"].clear()


def _instrument_shot_distance(acc: dict):
    """Monkeypatch para registrar desde donde se patea cada remate."""
    o_shoot = MatchEngine._shoot

    def shoot(self, owner, goal):
        acc["_shot_dists_this"].append(owner.position.distance_to(goal))
        return o_shoot(self, owner, goal)

    MatchEngine._shoot = shoot
    return o_shoot


def _fmt_row(name: str, ours: float, real: float | None) -> str:
    """Una fila de la tabla: nuestro valor, el real y una marca de estado."""
    if real is None:
        return f"  {name:<22} {ours:>7.1f}        -        -"
    ratio = ours / real if real else 0.0
    if 0.7 <= ratio <= 1.4:
        flag = "ok"
    elif ratio < 0.7:
        flag = "BAJO"
    else:
        flag = "ALTO"
    return f"  {name:<22} {ours:>7.1f} {real:>8.1f}   x{ratio:>4.2f}  {flag}"


def _print_stats(acc: dict, n: int) -> None:
    ev = acc["events"]
    per = lambda k: ev.get(k, 0) / n

    remates = per("remate") + per("cabezazo")
    on_target = per("gol") + per("atajada") + per("rebote") + per("escapa")
    poss_home = acc["poss"][Side.HOME]
    poss_total = poss_home + acc["poss"][Side.AWAY]
    poss_pct = 100.0 * poss_home / poss_total if poss_total else 50.0

    rows = [
        ("Remates (total)", remates, _REAL["Remates (total)"]),
        ("  de cabeza", per("cabezazo"), None),
        ("Remates al arco", on_target, _REAL["Remates al arco"]),
        ("Goles", per("gol"), _REAL["Goles"]),
        ("Atajadas", per("atajada"), _REAL["Atajadas"]),
        ("Corners", per("corner"), _REAL["Corners"]),
        ("Faltas", per("falta"), _REAL["Faltas"]),
        ("Offsides", per("offside"), _REAL["Offsides"]),
        ("Manos", per("mano"), None),
        ("Laterales", per("lateral"), _REAL["Laterales"]),
        ("Saques de arco", per("saque_arco"), None),
        ("Centros", per("centro"), None),
        ("Pases", per("pase") + per("saque_corto"), _REAL["Pases"]),
        ("Intercepciones", per("intercepta"), None),
        ("Quites", per("quite"), None),
        ("Despejes", per("despeje"), None),
        ("Posesion local %", poss_pct, _REAL["Posesion local %"]),
    ]

    print("=" * 60)
    print(f"  ESTADISTICAS DEL MOTOR  ({n} partidos de 600s)")
    print("=" * 60)
    print(f"  {'Metrica':<22} {'Motor':>7} {'Real':>8} {'Ratio':>7}  Estado")
    print("  " + "-" * 56)
    for name, ours, real in rows:
        print(_fmt_row(name, ours, real))
    print("  " + "-" * 56)
    print("  (Real = partido tipico de 90 min, ambos equipos. Ratio motor/real.)")
    print()

    # Distribucion de distancia de remate.
    dists = acc["shot_dists"]
    if dists:
        inside = sum(1 for d in dists if d < 16.5)
        edge = sum(1 for d in dists if 16.5 <= d < 25.0)
        far = sum(1 for d in dists if d >= 25.0)
        t = len(dists)
        print("  REMATES POR DISTANCIA:")
        print(f"    dentro del area (<16.5m)   {100*inside/t:>4.0f}%")
        print(f"    borde del area (16.5-25m)  {100*edge/t:>4.0f}%")
        print(f"    de lejos (>25m)            {100*far/t:>4.0f}%")
        print(f"    distancia media: {sum(dists)/t:.1f} m")
        print()


def _print_touches(acc: dict, n: int) -> None:
    touches = acc["touches"]
    total = sum(touches.values()) or 1
    order = ["GK", "CB", "FB", "MID", "WG", "ST"]
    names = {
        "GK": "Arquero", "CB": "Central", "FB": "Lateral",
        "MID": "Volante", "WG": "Extremo", "ST": "Delantero",
    }
    print("  TOQUES DE PELOTA POR POSICION:")
    print(f"    {'Posicion':<11} {'/partido':>9} {'% del total':>12}  barra")
    for r in order:
        c = touches.get(r, 0)
        pct = 100.0 * c / total
        bar = "#" * int(pct / 2)
        print(f"    {names[r]:<11} {c/n:>9.1f} {pct:>11.1f}%  {bar}")
    print()


def _print_heatmap(acc: dict) -> None:
    heat = acc["heat"]
    mx = max((max(r) for r in heat), default=0) or 1
    print("  HEATMAP DE LA PELOTA  (izq: arco local  ->  der: arco visitante)")
    border = "  +" + "-" * _HM_COLS + "+"
    print(border)
    for row in heat:
        line = "".join(
            _SHADES[min(len(_SHADES) - 1, int(v / mx * (len(_SHADES) - 1)))]
            for v in row
        )
        print("  |" + line + "|")
    print(border)
    print("  (mas denso = mas tiempo la pelota ahi; la mitad es el centro)")
    print()


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    base_seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    acc = {
        "events": Counter(),
        "scores": [],
        "heat": [[0] * _HM_COLS for _ in range(_HM_ROWS)],
        "touches": defaultdict(int),
        "poss": defaultdict(int),
        "shot_dists": [],
        "_shot_dists_this": [],
    }
    o_shoot = _instrument_shot_distance(acc)
    try:
        for i in range(n):
            _run_match(base_seed + i, acc)
            print(f"\r  corriendo... {i + 1}/{n}", end="", file=sys.stderr, flush=True)
    finally:
        MatchEngine._shoot = o_shoot
    print("\r" + " " * 30 + "\r", end="", file=sys.stderr)

    _print_stats(acc, n)
    _print_touches(acc, n)
    _print_heatmap(acc)


if __name__ == "__main__":
    main()
