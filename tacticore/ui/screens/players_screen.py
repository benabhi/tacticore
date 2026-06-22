"""Seccion Jugadores (placeholder por ahora)."""

from collections.abc import Iterator

from textual.widget import Widget
from textual.widgets import Static

from .section_screen import SectionScreen


class PlayersScreen(SectionScreen):
    """Plantilla del club. En construccion."""

    section_key = "J"

    def content(self) -> Iterator[Widget]:
        yield Static("JUGADORES\n")
        yield Static("(Plantilla, skills, estado y especialidades. Proximamente.)")
