"""Seccion Oficina: pantalla inicial del juego."""

from collections.abc import Iterator

from textual.widget import Widget
from textual.widgets import Static

from .section_screen import SectionScreen


class OfficeScreen(SectionScreen):
    """La oficina del manager (dashboard inicial)."""

    section_key = "O"

    def content(self) -> Iterator[Widget]:
        club = self.app.club_name or "Sin nombre"
        yield Static("OFICINA\n")
        yield Static(f"Bienvenido a {club}.\n")
        yield Static("(Aca va a ir el resumen del club: finanzas, proxima\n"
                     "fecha, novedades, etc. Proximamente.)")
