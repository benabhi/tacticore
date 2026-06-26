"""Constantes globales de configuracion del juego.

Toda la interfaz se disena para una resolucion fija de terminal. Si en el
futuro hace falta otra constante global (rutas, version del formato de
guardado, etc.) tambien vive aca.
"""

from datetime import date
from pathlib import Path

# Fecha en la que arranca una partida nueva (las edades se calculan contra la
# fecha del juego, que avanza con el calendario; ver core/calendar.py).
SEASON_START_DATE = date(2025, 7, 1)

# --- Resolucion objetivo de la terminal ---
# El juego completo se disena para este tamano exacto.
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 25

# Altura reservada para la barra de menu inferior (HUD).
MENU_BAR_HEIGHT = 1

# --- Generacion del mundo ---
# Cuantos paises generar. None = TODOS los disponibles (58). El mundo completo
# son ~2.320 clubes / ~37.000 jugadores: se genera en ~1.3s y el save pesa ~11MB.
WORLD_COUNTRY_COUNT: int | None = None
CLUBS_PER_LEAGUE = 8      # clubes en cada liga (mismo para los 5 niveles)
SQUAD_SIZE = 16           # jugadores por club

# Pausa (segundos) entre pasos de la barra de carga. Es solo "sabor": la
# generacion real es casi instantanea, asi se ve la barra llenarse. Poner 0
# para que sea instantaneo.
LOADING_STEP_DELAY = 0.015

# --- Rutas ---
# Carpeta raiz del proyecto (dos niveles arriba de este archivo).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Carpeta donde se guardan las partidas.
SAVE_DIR = PROJECT_ROOT / "saves"
# Dataset externo de nombres reales por pais (CSV por pais, ISO alpha2).
# Pesa ~10GB y esta gitignored; se usa como SOURCE para destilar una base de
# nombres compacta. Ver docs/DESIGN.md.
NAMES_DATASET_DIR = PROJECT_ROOT / "datasets" / "names"
