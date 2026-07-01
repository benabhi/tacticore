"""Tests de la alineacion automatica (auto_select sobre una formacion)."""

from tacticore.core.rng import new_rng
from tacticore.domain.enums import LeagueTier
from tacticore.generators import ClubGenerator
from tacticore.simulation.match.formation import FORMATION_11, auto_select


def _club(seed: int = 1):
    return ClubGenerator(new_rng(seed)).generate(squad_size=16, tier=LeagueTier.E)


def test_auto_select_fills_starters_and_bench():
    club = _club()
    lineup, bench = auto_select(club, FORMATION_11, bench_size=5)
    assert len(lineup) == FORMATION_11.size          # 11 titulares
    assert len(bench) == 5                            # banco pedido
    # Titulares y banco son jugadores del club, sin repetir entre si.
    ids = [id(p) for p in lineup + bench]
    assert len(ids) == len(set(ids))
    assert all(p in club.players for p in lineup + bench)


def test_auto_select_bench_is_best_of_the_rest():
    club = _club(3)
    lineup, bench = auto_select(club, FORMATION_11, bench_size=5)
    used = {id(p) for p in lineup}
    rest = sorted((p for p in club.players if id(p) not in used),
                  key=lambda p: p.overall, reverse=True)
    assert [id(p) for p in bench] == [id(p) for p in rest[:5]]
