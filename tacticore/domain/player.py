"""Entidad Jugador.

Atributos pensados para el partido en tiempo real (ver docs/DESIGN.md, seccion
3). Escala 1.0-100.0 con decimales: permite progreso fino por entreno/partido
(ej. +0.59) sin techos rapidos. Sin etiquetas tipo "pobre/divino".
"""

from dataclasses import dataclass, field
from datetime import date

from .enums import Foot, Morale, Position, Specialty
from .injury import Injury

# Atributos agrupados (todos float 1-100). El orden es el que usa el generador.
PHYSICAL_ATTRS = ("speed", "acceleration", "stamina", "strength", "agility", "jumping")
TECHNICAL_ATTRS = ("passing", "shooting", "dribbling", "tackling", "heading")
MENTAL_ATTRS = ("vision", "positioning", "anticipation", "composure", "work_rate")
GK_ATTRS = ("reflexes", "handling", "aerial_reach")
ALL_ATTRS = PHYSICAL_ATTRS + TECHNICAL_ATTRS + MENTAL_ATTRS + GK_ATTRS

# Pesos por posicion para el overall: que atributos importan y cuanto. Es
# provisional; la simulacion real usa los atributos crudos, no este promedio.
_OVERALL_WEIGHTS: dict[Position, dict[str, int]] = {
    Position.GOALKEEPER: {
        "reflexes": 3, "handling": 2, "aerial_reach": 2, "positioning": 1,
        "anticipation": 1,
    },
    Position.DEFENDER: {
        "tackling": 3, "positioning": 2, "strength": 1, "heading": 1,
        "anticipation": 1, "speed": 1, "passing": 1,
    },
    Position.MIDFIELDER: {
        "passing": 3, "vision": 2, "dribbling": 1, "work_rate": 1,
        "positioning": 1, "stamina": 1, "tackling": 1,
    },
    Position.FORWARD: {
        "shooting": 3, "dribbling": 2, "speed": 1, "positioning": 1,
        "heading": 1, "passing": 1,
    },
}


@dataclass
class Player:
    """Un jugador del juego."""

    # --- Identidad ---
    first_name: str
    last_name: str
    nationality: str          # codigo de pais ISO alpha2 (ej. "AR")
    position: Position
    foot: Foot
    birth_date: date          # la edad se calcula contra la fecha del juego
    height_cm: int
    weight_kg: int

    # --- Atributos fisicos (1-100) ---
    speed: float = 1.0
    acceleration: float = 1.0
    stamina: float = 1.0
    strength: float = 1.0
    agility: float = 1.0
    jumping: float = 1.0

    # --- Atributos tecnicos (1-100) ---
    passing: float = 1.0
    shooting: float = 1.0
    dribbling: float = 1.0
    tackling: float = 1.0
    heading: float = 1.0

    # --- Atributos mentales (1-100) ---
    vision: float = 1.0
    positioning: float = 1.0
    anticipation: float = 1.0
    composure: float = 1.0
    work_rate: float = 1.0

    # --- Atributos de arquero (1-100; bajos en jugadores de campo) ---
    reflexes: float = 1.0
    handling: float = 1.0
    aerial_reach: float = 1.0

    # --- Estado dinamico (cambia al pasar fechas / en el partido) ---
    form: float = 50.0        # estado de forma actual (1-100)
    fitness: float = 100.0    # energia disponible (0-100)
    morale: Morale = Morale.NEUTRAL
    injury: Injury | None = None

    # --- Rasgos ---
    specialty: Specialty | None = None  # 0 o 1 (raro)
    nickname: str | None = None         # alias, ej. "La Pulga"
    shirt_number: int | None = None     # lo asigna el club
    origin_club: str | None = None      # club de origen / cantera

    # --- Ocultos / desarrollo ---
    potential: float = 1.0          # techo de habilidad (1-100)
    injury_proneness: float = 50.0  # propension a lesionarse (1-100)
    injury_history: list[Injury] = field(default_factory=list)

    def age_on(self, today: date) -> int:
        """Edad en anios cumplidos a la fecha `today` (la del juego).

        Como guardamos la fecha de nacimiento (no la edad), el jugador envejece
        solo al avanzar el calendario.
        """
        years = today.year - self.birth_date.year
        if (today.month, today.day) < (self.birth_date.month, self.birth_date.day):
            years -= 1
        return years

    @property
    def full_name(self) -> str:
        """Nombre y apellido."""
        return f"{self.first_name} {self.last_name}"

    @property
    def display_name(self) -> str:
        """Nombre para mostrar: usa el alias si lo tiene."""
        return self.nickname or self.full_name

    @property
    def is_injured(self) -> bool:
        """Si tiene una lesion activa."""
        return self.injury is not None

    @property
    def overall(self) -> float:
        """Media ponderada de los atributos relevantes a su posicion (1-100)."""
        weights = _OVERALL_WEIGHTS[self.position]
        total = sum(getattr(self, attr) * w for attr, w in weights.items())
        return round(total / sum(weights.values()), 1)
