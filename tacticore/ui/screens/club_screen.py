"""Seccion Club (placeholder por ahora)."""

from collections.abc import Iterator

from textual.widget import Widget
from textual.widgets import Static

from .section_screen import SectionScreen


class ClubScreen(SectionScreen):
    """Datos del club (estadio, finanzas, socios). En construccion."""

    section_key = "C"

    def content(self) -> Iterator[Widget]:
        yield Static("CLUB\n")
        yield Static("(Estadio, capital, socios, instalaciones. Proximamente.)")
