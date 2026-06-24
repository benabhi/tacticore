"""Demo de desarrollo: mira un partido en vivo en la terminal.

Uso (con el venv activado):

    python scripts/watch_match.py            # partido NUEVO al azar cada vez
    python scripts/watch_match.py 12345      # repite exactamente la semilla 12345

Sin argumento, cada corrida genera un cruce distinto (nacionalidades, clubes y
desarrollo) y al salir te imprime la semilla para que puedas repetirlo. Con una
semilla, el partido es identico (es la base del replay determinista).

ESPACIO pausa, Q sale. Es una herramienta de desarrollo, no parte del flujo del
juego (eso se integra en la Fase C).
"""

import random
import sys
from pathlib import Path

# Permite ejecutar el script directo (agrega la raiz del repo al path).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from textual.app import App

from tacticore.core.rng import new_rng
from tacticore.domain.enums import LeagueTier
from tacticore.generators import ClubGenerator
from tacticore.simulation.match import FORMATIONS_11
from tacticore.ui.screens.match_screen import MatchScreen

# Paises con pool de nombres disponible (ver generators/data/names/).
_COUNTRIES = ["AR", "BE", "BR", "CL", "CO", "DE", "ES", "FR",
              "GB", "IT", "JP", "MX", "NL", "PT", "US", "UY"]


def _build_match(seed: int):
    """Arma dos clubes y el contexto del partido de forma reproducible por seed."""
    setup = new_rng(seed)
    home_cc, away_cc = setup.sample(_COUNTRIES, 2)
    tier = setup.choice(list(LeagueTier))
    gen = ClubGenerator(setup)
    home = gen.generate(squad_size=16, country_code=home_cc, tier=tier)
    away = gen.generate(squad_size=16, country_code=away_cc, tier=tier)
    home_formation = setup.choice(FORMATIONS_11)
    away_formation = setup.choice(FORMATIONS_11)
    return home, away, home_cc, away_cc, tier, home_formation, away_formation


class _WatchApp(App):
    """App minima que abre directamente un partido de prueba."""

    CSS = "Screen { background: black; }"

    def __init__(self, seed: int) -> None:
        super().__init__()
        self._seed = seed

    def on_mount(self) -> None:
        home, away, _hc, _ac, _t, hf, af = _build_match(self._seed)
        # El partido en si usa su propia corriente determinista por la misma seed.
        self.push_screen(
            MatchScreen(home, away, seed=self._seed, home_formation=hf, away_formation=af)
        )


if __name__ == "__main__":
    if len(sys.argv) > 1:
        seed = int(sys.argv[1])
    else:
        seed = random.randint(1, 9_999_999)

    home, away, home_cc, away_cc, tier, hf, af = _build_match(seed)
    print(f"Partido: {home.short_name} ({home_cc}, {hf.name}) vs "
          f"{away.short_name} ({away_cc}, {af.name})  -  liga {tier.value}")
    print(f"Semilla: {seed}   (repetilo con: python scripts/watch_match.py {seed})")

    _WatchApp(seed).run()

    # Al salir, recordamos la semilla por si queres volver a verlo.
    print(f"\nSemilla de ese partido: {seed}")
