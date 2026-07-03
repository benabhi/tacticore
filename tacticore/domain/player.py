"""Entidad Jugador.

Atributos pensados para el partido en tiempo real (ver docs/DESIGN.md, seccion
3). Escala 1.0-100.0 con decimales: permite progreso fino por entreno/partido
(ej. +0.59) sin techos rapidos. Sin etiquetas tipo "pobre/divino".
"""

from dataclasses import dataclass, field
from datetime import date

from .enums import Foot, Morale, Position, Specialty
from .injury import Injury
from .positions import POSITION_PRIORITIES

# Atributos agrupados en 3 categorias de 5 (todos float 1-100). Son GENERALES:
# sirven para cualquier jugador. El arquero no tiene atributos propios; se apoya
# en los generales (agilidad, posicion, anticipacion, temple, juego aereo).
PHYSICAL_ATTRS = ("speed", "stamina", "strength", "agility", "aerial")
TECHNICAL_ATTRS = ("passing", "shooting", "dribbling", "tackling", "crossing")
MENTAL_ATTRS = ("vision", "positioning", "anticipation", "composure", "work_rate")
ALL_ATTRS = PHYSICAL_ATTRS + TECHNICAL_ATTRS + MENTAL_ATTRS

# Pesos por posicion para el overall: se derivan de los atributos prioritarios de
# cada posicion (mas importante -> mas peso). Es provisional; la simulacion real
# usa los atributos crudos, no este promedio.
_RANK_WEIGHTS = (5, 4, 3, 2, 1)
_OVERALL_WEIGHTS: dict[Position, dict[str, int]] = {
    position: {attr: _RANK_WEIGHTS[i] for i, attr in enumerate(attrs)}
    for position, attrs in POSITION_PRIORITIES.items()
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
    stamina: float = 1.0
    strength: float = 1.0
    agility: float = 1.0
    aerial: float = 1.0      # juego aereo: saltar, ganar de cabeza, salir a cruces

    # --- Atributos tecnicos (1-100) ---
    passing: float = 1.0
    shooting: float = 1.0
    dribbling: float = 1.0
    tackling: float = 1.0
    crossing: float = 1.0    # precision/peligro del centro

    # --- Atributos mentales (1-100) ---
    vision: float = 1.0
    positioning: float = 1.0
    anticipation: float = 1.0
    composure: float = 1.0
    work_rate: float = 1.0

    # --- Estado dinamico (cambia al pasar fechas / en el partido) ---
    form: float = 50.0        # estado de forma actual (1-100)
    fitness: float = 100.0    # energia disponible (0-100)
    experience: float = 1.0   # experiencia (1-100): sube con la edad y los partidos
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

    # --- Mercado ---
    asking_price: int | None = None  # si esta seteado, esta a la venta a ese precio

    def age_on(self, today: date) -> int:
        """Edad en anios cumplidos a la fecha `today` (la del juego).

        Como guardamos la fecha de nacimiento (no la edad), el jugador envejece
        solo al avanzar el calendario.
        """
        years = today.year - self.birth_date.year
        if (today.month, today.day) < (self.birth_date.month, self.birth_date.day):
            years -= 1
        return years

    def age_parts_on(self, today: date) -> tuple[int, int]:
        """Edad como (anios cumplidos, dias desde el ultimo cumpleanios).

        Para mostrar la edad fina en la ficha (ej. "28 anios 145 dias"). Los
        dias salen de restar la fecha del ultimo aniversario ya cumplido.
        """
        years = self.age_on(today)
        last_birthday = self.birth_date.replace(year=self.birth_date.year + years)
        return years, (today - last_birthday).days

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
