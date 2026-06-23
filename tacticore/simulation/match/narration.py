"""Relato del partido: convierte un `MatchEvent` en una linea de texto (ES).

Version basica: una plantilla por tipo de evento. Mas adelante esto crece a un
sistema con variantes/aleatoriedad por evento (ver docs/DESIGN.md). El texto va
en espanol y ASCII (directivas 2 y 4) y nunca pasa de 80 caracteres.
"""

from .events import MatchEvent

# Limite duro de ancho (la terminal es de 80 columnas).
MAX_WIDTH = 80

_TEMPLATES: dict[str, str] = {
    "gol": "GOOOL! Lo grita {who}!",
    "remate": "{who} remata al arco!",
    "despeje": "{who} despeja la pelota",
    "atajada": "Gran atajada de {who}!",
    "rebote": "{who} no la retiene, la pelota queda viva!",
    "quite": "{who} mete el pie y recupera",
    "falta": "Falta de {who}",
    "offside": "Posicion adelantada de {who}",
    "mano": "Mano de {who}!",
    "lateral": "La pelota sale: lateral",
    "corner": "Sale al corner, tiro de esquina",
    "saque_arco": "Saque de arco",
}


def narrate(event: MatchEvent) -> str:
    """Devuelve la linea de relato para un evento (<= 80 chars, ASCII/ES)."""
    who = event.player or "el equipo"
    text = _TEMPLATES.get(event.kind, event.kind).format(who=who)
    return text[:MAX_WIDTH]
