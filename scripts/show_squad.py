"""Demo de desarrollo: imprime la tabla de un plantel generado.

Uso (con el venv activado):

    python scripts/show_squad.py [seed]

Muestra la lista del plantel (resumen) y la ficha completa del mejor jugador,
con los datos que veria el manager. Las edades se calculan contra la fecha de
inicio de temporada (config.SEASON_START_DATE).
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tacticore import config
from tacticore.core.rng import new_rng
from tacticore.domain.enums import Foot, LeagueTier, Position
from tacticore.generators import ClubGenerator

_POS = {Position.GOALKEEPER: "ARQ", Position.DEFENDER: "DEF",
        Position.MIDFIELDER: "MED", Position.FORWARD: "DEL"}
_FOOT = {Foot.LEFT: "Zurdo", Foot.RIGHT: "Diestro", Foot.BOTH: "Ambidiestro"}
_MORALE = {1: "Destrozado", 2: "Bajoneado", 3: "Neutral", 4: "Contento", 5: "Encendido"}
_TODAY = config.SEASON_START_DATE


def _i(x):
    return int(round(x))


def _attr(label, value):
    return f"{label:<13}{_i(value):>3}"


def show(club):
    print(f"== {club.name} ({club.country_code})  -  Liga {club.tier.value}  "
          f"-  OVR equipo {_i(club.overall)} ==")
    print()
    print(" #  NOMBRE                 POS NAC EDA OVR POT FOR FIS  MORAL       ESTADO")
    print("--- ---------------------- --- --- --- --- --- --- ---  ----------  ---------")
    for p in sorted(club.players, key=lambda p: p.shirt_number or 99):
        estado = "Lesionado" if p.is_injured else "Sano"
        print(f"{p.shirt_number:>2}  {p.display_name:<22.22} {_POS[p.position]:<3} "
              f"{p.nationality:<3} {p.age_on(_TODAY):>3} {_i(p.overall):>3} "
              f"{_i(p.potential):>3} {_i(p.form):>3} {_i(p.fitness):>3}  "
              f"{_MORALE[p.morale.value]:<10}  {estado}")

    # Ficha del mejor jugador.
    star = max(club.players, key=lambda p: p.overall)
    alias = f' "{star.nickname}"' if star.nickname else ""
    print()
    print("+" + "-" * 76 + "+")
    print(f"| #{star.shirt_number:<3}{star.full_name}{alias}".ljust(50)
          + f"{_POS[star.position]}  Pie: {_FOOT[star.foot]}".ljust(26) + "|")
    print(f"| Nac: {star.nationality}   Nac. {star.birth_date.strftime('%d/%m/%Y')}   "
          f"Edad {star.age_on(_TODAY)}   {star.height_cm}cm/{star.weight_kg}kg   "
          f"OVR {_i(star.overall)}  POT {_i(star.potential)}".ljust(74) + " |")
    esp = star.specialty.name if star.specialty else "-"
    print(f"| Cantera: {star.origin_club}   Especialidad: {esp}".ljust(76) + "|")
    print("+" + "-" * 76 + "+")
    cols = [
        [_attr("Velocidad", star.speed), _attr("Resistencia", star.stamina),
         _attr("Fuerza", star.strength), _attr("Agilidad", star.agility),
         _attr("J. aereo", star.aerial)],
        [_attr("Pase", star.passing), _attr("Remate", star.shooting),
         _attr("Gambeta", star.dribbling), _attr("Quite", star.tackling),
         _attr("Centro", star.crossing)],
        [_attr("Vision", star.vision), _attr("Posicion", star.positioning),
         _attr("Anticipacion", star.anticipation), _attr("Compostura", star.composure),
         _attr("Sacrificio", star.work_rate)],
    ]
    print("FISICO            TECNICO           MENTAL")
    for i in range(5):
        row = [(c[i] if i < len(c) else " " * 16) for c in cols]
        print("  ".join(row).rstrip())


if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else random.randint(1, 9_999_999)
    gen = ClubGenerator(new_rng(seed))
    cc = new_rng(seed).choice(["AR", "BR", "ES", "IT", "FR", "DE", "UY"])
    tier = new_rng(seed).choice(list(LeagueTier))
    show(gen.generate(squad_size=16, country_code=cc, tier=tier))
    print(f"\n(seed {seed})")
