"""Entidad Estadio.

El estadio se divide en cuatro SECTORES de asientos (estilo Hattrick), cada uno
con su precio de entrada fijo (ver simulation/economy.py): general (el mas barato)
-> preferente -> tribuna -> palco (el mas caro). La capacidad total es la suma de
los cuatro. Se pueden sumar asientos por sector (ampliaciones); la recaudacion de
un partido de local depende de cuantos se llenen y a que precio.
"""

from dataclasses import dataclass


@dataclass
class Stadium:
    """El estadio de un club, por sectores de asientos."""

    name: str
    general: int = 0     # grada general (el sector mas barato y numeroso)
    preferente: int = 0  # preferente
    tribuna: int = 0     # tribuna
    palco: int = 0       # palcos (el mas caro; solo en clubes grandes)

    @property
    def capacity(self) -> int:
        """Capacidad total: la suma de los cuatro sectores."""
        return self.general + self.preferente + self.tribuna + self.palco
