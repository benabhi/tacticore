"""Demo de desarrollo: mira un partido en vivo en la terminal.

Uso (con el venv activado):

    python scripts/watch_match.py [seed]

Genera dos clubes de fantasia y abre la pantalla de partido corriendo el motor.
ESPACIO pausa, Q sale. Es una herramienta de desarrollo, no parte del flujo del
juego (eso se integra en la Fase C).
"""

import sys
from pathlib import Path

# Permite ejecutar el script directo (agrega la raiz del repo al path).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from textual.app import App

from tacticore.core.rng import new_rng
from tacticore.domain.enums import LeagueTier
from tacticore.generators import ClubGenerator
from tacticore.ui.screens.match_screen import MatchScreen


class _WatchApp(App):
    """App minima que abre directamente un partido de prueba."""

    CSS = "Screen { background: black; }"

    def __init__(self, seed: int) -> None:
        super().__init__()
        self._seed = seed

    def on_mount(self) -> None:
        gen = ClubGenerator(new_rng(42))
        home = gen.generate(squad_size=16, country_code="AR", tier=LeagueTier.C)
        away = gen.generate(squad_size=16, country_code="BR", tier=LeagueTier.C)
        self.push_screen(MatchScreen(home, away, seed=self._seed))


if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    _WatchApp(seed).run()
