"""Escalera de niveles nombrados para los skills (estilo Hattrick).

Los skills se guardan como enteros 1-20 para simular; estos nombres son solo
para mostrarlos en pantalla de forma mas evocadora.
"""

# Indice 0 -> nivel 1, ..., indice 19 -> nivel 20.
SKILL_LEVELS = (
    "desastroso",      # 1
    "horrible",        # 2
    "pobre",           # 3
    "debil",           # 4
    "insuficiente",    # 5
    "pasable",         # 6
    "aceptable",       # 7
    "bueno",           # 8
    "muy bueno",       # 9
    "excelente",       # 10
    "formidable",      # 11
    "brillante",       # 12
    "magnifico",       # 13
    "clase mundial",   # 14
    "sobrenatural",    # 15
    "titanico",        # 16
    "extraterrestre",  # 17
    "magico",          # 18
    "utopico",         # 19
    "divino",          # 20
)

SKILL_MIN = 1
SKILL_MAX = 20


def skill_level_name(value: int) -> str:
    """Devuelve el nombre del nivel para un valor de skill (1-20)."""
    value = max(SKILL_MIN, min(SKILL_MAX, value))
    return SKILL_LEVELS[value - 1]
