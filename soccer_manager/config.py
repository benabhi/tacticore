"""Constantes globales de configuracion del juego.

Toda la interfaz se disena para una resolucion fija de terminal. Si en el
futuro hace falta otra constante global (rutas, version del formato de
guardado, etc.) tambien vive aca.
"""

from pathlib import Path

# --- Resolucion objetivo de la terminal ---
# El juego completo se disena para este tamano exacto.
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 25

# Altura reservada para la barra de menu inferior (HUD).
MENU_BAR_HEIGHT = 1

# --- Rutas ---
# Carpeta raiz del proyecto (dos niveles arriba de este archivo).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Carpeta donde se guardan las partidas.
SAVE_DIR = PROJECT_ROOT / "saves"
