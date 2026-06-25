"""Relato del partido: convierte un `MatchEvent` en texto (ES).

Version basica: una plantilla por tipo de evento. Mas adelante esto crece a un
sistema con variantes/aleatoriedad por evento (ver docs/DESIGN.md). El texto va
en espanol y ASCII (directivas 2 y 4).

`narrate_segments` devuelve la frase partida en tramos marcando cuales son
NOMBRES de jugador, para que la UI los resalte con el color del equipo (la
narracion no conoce colores: separa logica de presentacion).
"""

import re

from .events import MatchEvent

# Limite del texto del relato (deja lugar para el reloj que antepone la UI).
MAX_WIDTH = 72

# {who} = protagonista, {target} = segundo jugador, {detail} = matiz.
_TEMPLATES: dict[str, str] = {
    "gol": "GOOOL! La clava {who} y hace estallar el estadio!",
    "remate": "{who} se anima y saca un remate al arco!",
    "cabezazo": "{who} salta y cabecea al arco!",
    "pase": "{who} prueba un pase {detail} para {target}",
    "centro": "{who} desborda por la banda y tira el centro al area!",
    "despeje": "{who} despeja{detail} y la saca del area",
    "saque_corto": "{who} saca corto y juega para {target}",
    "atajada": "Gran atajada de {who}, le tapa el remate!",
    "escapa": "Se le escapa de las manos a {who}!",
    "rebote": "{who} no la pudo retener, queda viva en el area!",
    "quite": "{who} mete el pie firme y le saca la pelota",
    "intercepta": "{who} se anticipa y corta la jugada!",
    "falta": "Falta de {who}, el arbitro detiene el juego",
    "offside": "{who} salio adelantado, el juez marca offside",
    "mano": "Mano de {who}! El arbitro la vio clarita",
    "lateral": "La pelota se fue por la linea, hay saque lateral",
    "corner": "Rechazo al corner, viene el tiro de esquina",
    "saque_arco": "Se fue al fondo, sera saque de arco",
}

_TOKENS = re.compile(r"(\{who\}|\{target\}|\{detail\})")


def narrate_segments(event: MatchEvent) -> list[tuple[str, bool]]:
    """Parte la frase en tramos `(texto, es_nombre)` para que la UI los coloree."""
    tpl = _TEMPLATES.get(event.kind, event.kind)
    fills = {
        "{who}": (event.player or "el equipo", True),
        "{target}": (event.target or "un companero", True),
        "{detail}": (event.detail or "", False),
    }
    segments: list[tuple[str, bool]] = []
    for part in _TOKENS.split(tpl):
        if part in fills:
            text, is_name = fills[part]
            if text:
                segments.append((text, is_name))
        elif part:
            segments.append((part, False))
    return segments


def narrate(event: MatchEvent) -> str:
    """Linea de relato en texto plano (<= MAX_WIDTH, ASCII/ES)."""
    line = "".join(text for text, _ in narrate_segments(event))
    return line[:MAX_WIDTH]
