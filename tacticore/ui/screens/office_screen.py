"""Seccion Oficina: pantalla inicial del juego."""

from collections.abc import Iterator

from textual.widget import Widget
from textual.widgets import Static

from .section_screen import SectionScreen


class OfficeScreen(SectionScreen):
    """La oficina del manager (dashboard inicial)."""

    section_key = "O"

    def content(self) -> Iterator[Widget]:
        game = self.app.game
        club = game.player_club if game else None
        if club is None:
            yield Static("OFICINA\n")
            yield Static("(Sin club todavia.)")
            return
        president = game.president_name or "Presidente"
        yield Static("OFICINA\n")
        yield Static(f"Bienvenido a {club.name}, {president}.\n")
        yield Static(
            f"Liga: {club.tier.value}   Socios: {club.members}   "
            f"Capital: {club.capital:,}\n"
            f"Estadio: {club.stadium.name} ({club.stadium.capacity:,})\n"
            f"Hinchada: {club.fans_name}\n"
            f"DT: {club.manager.full_name if club.manager else '-'}\n"
            f"Plantilla: {club.squad_size} jugadores"
        )
