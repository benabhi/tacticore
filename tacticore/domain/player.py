"""Entidad Jugador.

Modelo de atributos al estilo Hattrick: pocos skills principales (1-20), unos
de soporte, estado dinamico (forma, moral, lesion) y a lo sumo una especialidad
rara. Pensado para alimentar simulaciones complejas mas adelante.
"""

from dataclasses import dataclass, field

from .enums import Foot, Morale, Position, Specialty
from .injury import Injury

# Pesos por posicion para el calculo del overall: que skills importan y cuanto.
# Es provisional; la simulacion real usara los skills crudos, no este promedio.
_OVERALL_WEIGHTS: dict[Position, dict[str, int]] = {
    Position.GOALKEEPER: {"goalkeeping": 3, "defending": 1, "set_pieces": 1},
    Position.DEFENDER: {
        "defending": 3, "passing": 1, "playmaking": 1, "winger": 1, "set_pieces": 1,
    },
    Position.MIDFIELDER: {
        "playmaking": 3, "passing": 2, "winger": 1, "scoring": 1, "defending": 1,
        "set_pieces": 1,
    },
    Position.FORWARD: {
        "scoring": 3, "passing": 1, "winger": 1, "playmaking": 1, "set_pieces": 1,
    },
}


@dataclass
class Player:
    """Un jugador del juego."""

    # --- Identidad ---
    first_name: str
    last_name: str
    position: Position
    foot: Foot
    age: int
    height_cm: int
    weight_kg: int

    # --- Skills principales (1-20) ---
    goalkeeping: int = 1
    defending: int = 1
    playmaking: int = 1
    winger: int = 1
    passing: int = 1
    scoring: int = 1
    set_pieces: int = 1

    # --- Skills de soporte (1-20) ---
    stamina: int = 1      # resistencia: cuanto aguanta el partido
    experience: int = 1   # experiencia: sube jugando
    leadership: int = 1   # liderazgo

    # --- Estado dinamico (cambia al pasar fechas) ---
    form: int = 10            # estado de forma actual (1-20)
    fitness: int = 100        # energia disponible (0-100)
    morale: Morale = Morale.NEUTRAL
    injury: Injury | None = None

    # --- Rasgos ---
    specialty: Specialty | None = None  # 0 o 1 (estilo Hattrick)
    nickname: str | None = None         # alias raro, ej. "La Pulga"
    shirt_number: int | None = None     # lo asigna el club
    origin_club: str | None = None      # club de origen / cantera

    # --- Ocultos / desarrollo ---
    potential: int = 1          # techo de habilidad (1-20)
    injury_proneness: int = 10  # propension a lesionarse (1-20)
    injury_history: list[Injury] = field(default_factory=list)

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
    def overall(self) -> int:
        """Media ponderada de los skills relevantes a su posicion (1-20)."""
        weights = _OVERALL_WEIGHTS[self.position]
        total = sum(getattr(self, skill) * w for skill, w in weights.items())
        return round(total / sum(weights.values()))
