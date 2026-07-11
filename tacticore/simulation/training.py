"""Entrenamiento por atributo: desarrollo de jugadores agrupados por habilidad.

Cada jugador del club del jugador puede entrenar UN atributo por semana
(`Player.training_focus`, exclusivo). El jueves se resuelve: por atributo, cada jugador
asignado tira su ganancia segun una CURVA con techo BLANDO (la capacidad de entreno del
club = DT + Centro de entrenamiento + staff) y techo DURO (su potencial). Las ganancias
son chicas y con suerte (a veces 0). Determinista con el `random.Random` que se pasa.

Sin UI: deja una notificacion (categoria "entrenamiento") con el resumen.
"""

import math
from datetime import date

from ..domain.player import ALL_ATTRS
from . import facilities as fac
from . import notifications as notif
from . import staff

# Los 15 atributos entrenables (fisicos/tecnicos/mentales).
TRAINABLE = ALL_ATTRS

# Etiquetas en espanol (replicadas de ui/player_labels para no importar UI, como
# discipline._TYPE_ES). Ver ATTR_LABEL alla si se agregan atributos.
_ATTR_ES = {
    "speed": "Velocidad", "stamina": "Resistencia", "strength": "Fuerza",
    "agility": "Agilidad", "aerial": "Juego aereo", "passing": "Pase",
    "shooting": "Remate", "dribbling": "Regate", "tackling": "Entrada",
    "crossing": "Centro", "vision": "Vision", "positioning": "Posicion",
    "anticipation": "Anticipacion", "composure": "Temple", "work_rate": "Sacrificio",
}

_W = 5.0          # ancho de la sigmoide (que tan blando es el techo)
_BASE = 0.85      # ganancia base (calibrada al arnes)
_LUCK_MAX = 1.4   # varianza de la semana (media ~0.7; a veces ~0)


def attr_label(attr: str) -> str:
    return _ATTR_ES.get(attr, attr)


def capacity(club) -> float:
    """Techo blando de entreno (1-100): DT + Centro de entrenamiento + bonus de staff."""
    base = club.coach.skill if club.coach else 40.0
    c = base + fac.training_capacity_pts(club) + staff.training_bonus(club)
    return max(1.0, min(100.0, c))


def _age_factor(age: int) -> float:
    """Los jovenes entrenan mucho mas rapido que los veteranos."""
    if age <= 21:
        return 1.2
    if age <= 25:
        return 1.0
    if age <= 29:
        return 0.7
    if age <= 32:
        return 0.4
    return 0.2


def can_improve(player, attr: str, cap: float) -> bool:
    """True si `attr` de `player` todavia tiene margen para subir (debajo del techo)."""
    x = getattr(player, attr)
    return x < player.potential - 0.05 and x < cap + 2 * _W


def train_gain(player, attr: str, cap: float, group_size: int,
               today: date, rng) -> float:
    """Ganancia de la semana en `attr` (aplica el cambio; 0 si no avanza)."""
    x = getattr(player, attr)
    pot = player.potential
    if x >= pot:
        return 0.0
    eff = 1.0 / (1.0 + math.exp((x - cap) / _W))     # sigmoide: ~1 debajo de cap, ->0 arriba
    age_factor = _age_factor(player.age_on(today))
    group_factor = 1.0 / math.sqrt(group_size)        # mas jugadores, menos atencion
    rate = 0.6 + cap / 100
    luck = rng.uniform(0.0, _LUCK_MAX)
    gain = _BASE * rate * eff * age_factor * group_factor * luck
    new_x = min(pot, round(x + gain, 1))
    setattr(player, attr, new_x)
    return round(new_x - x, 1)


# --- Asignacion de grupos (foco exclusivo por jugador) ---
def assign(player, attr: str) -> None:
    """Pone el foco de entreno del jugador en `attr` (saca el anterior)."""
    player.training_focus = attr if attr in TRAINABLE else None


def clear(player) -> None:
    player.training_focus = None


def group_for(club, attr: str) -> list:
    """Jugadores del club con foco en `attr`."""
    return [p for p in club.players if p.training_focus == attr]


def group_counts(club) -> dict[str, int]:
    """Cuantos jugadores entrenan cada atributo (para la UI)."""
    counts: dict[str, int] = {}
    for p in club.players:
        if p.training_focus in TRAINABLE:
            counts[p.training_focus] = counts.get(p.training_focus, 0) + 1
    return counts


# --- Resolucion semanal (jueves) ---
def run_training(game, rng, today: date) -> None:
    """Entrena a los jugadores asignados del club del jugador y notifica el resumen."""
    club = game.player_club
    if club is None:
        return
    cap = capacity(club)
    # Cada entrenamiento reinicia las mejoras mostradas: solo se ven las de ESTA semana.
    for p in club.players:
        p.last_gains = {}
    groups: dict[str, list] = {}
    for p in club.players:
        if p.training_focus in TRAINABLE:
            groups.setdefault(p.training_focus, []).append(p)
    if not groups:
        return
    results = []  # (player, attr, gain>0)
    for attr, players in groups.items():
        for p in players:
            g = train_gain(p, attr, cap, len(players), today, rng)
            if g > 0:
                results.append((p, attr, g))
                p.last_gains[attr] = g   # se resalta en verde en la ficha del jugador
    _notify(game, cap, sum(len(v) for v in groups.values()), results)


def _notify(game, cap: float, trained: int, results: list) -> None:
    """Notificacion COMPLETA del entreno de la semana: capacidad, cuantos entrenaron y
    la lista entera de mejoras (jugador + cuanto subio + atributo), de mayor a menor.

    El detalle va en el `message` (una mejora por renglon): la pantalla de
    Entrenamiento lo muestra completo y la lista de notificaciones, resumido."""
    if not results:
        notif.notify(
            game, "Entrenamiento: nadie mejoro",
            f"Entrenaron {trained} jugadores pero ninguno mejoro esta semana "
            f"(capacidad {cap:.0f}). A veces la semana sale seca; segui insistiendo.",
            notif.TRAINING)
        return
    lines = [f"Capacidad {cap:.0f}. Entrenaron {trained}, mejoraron {len(results)}:"]
    for p, a, g in sorted(results, key=lambda r: -r[2]):
        lines.append(f"  {p.full_name} +{g:.1f} {attr_label(a)}")
    notif.notify(
        game, f"Entrenamiento: {len(results)} mejoras",
        "\n".join(lines), notif.TRAINING)
