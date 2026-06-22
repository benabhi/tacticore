"""Guardado y carga del estado de la partida.

ESQUELETO: serializara/deserializara `GameState` a disco (en `config.SAVE_DIR`).
La estrategia concreta (JSON, pickle, etc.) se define mas adelante.
"""

from ..core.game import GameState


def save_game(state: GameState, name: str) -> None:
    """Guarda la partida en disco con el nombre dado."""
    raise NotImplementedError("Pendiente: serializacion del estado.")


def load_game(name: str) -> GameState:
    """Carga una partida guardada por su nombre."""
    raise NotImplementedError("Pendiente: deserializacion del estado.")
