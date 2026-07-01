"""Entidad Tactica: el planteo del equipo para UN partido.

Se asigna por partido (cada encuentro tiene su propia tactica). Por ahora guarda
la mentalidad y la tactica general; mas adelante sumara la formacion, los 11
titulares, los suplentes y las instrucciones finas. La pantalla completa donde se
arma (con la cancha) se trabaja aparte: es una pieza central del simulador.
"""

from dataclasses import dataclass

from .enums import Mentality, TeamTactic


@dataclass
class Tactic:
    """Planteo de un equipo para un partido concreto."""

    mentality: Mentality = Mentality.NEUTRAL
    team_tactic: TeamTactic = TeamTactic.NORMAL
    # Futuro: formacion, titulares, suplentes, instrucciones por jugador.
