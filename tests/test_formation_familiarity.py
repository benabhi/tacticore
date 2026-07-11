"""Familiaridad de formacion: sube al jugar (ganancia) e influye en el partido (efecto)."""

from tacticore.core.rng import new_rng
from tacticore.domain.club import Club
from tacticore.domain.enums import LeagueTier
from tacticore.domain.stadium import Stadium
from tacticore.generators import PlayerGenerator
from tacticore.simulation import formation_training as ft
from tacticore.simulation.match_engine import simulate_match


def _club(seed=0):
    c = Club(name="X", short_name="X", country_code="ES", tier=LeagueTier.C,
             stadium=Stadium(name="S"))
    c.players = [PlayerGenerator(new_rng(seed * 100 + i)).generate() for i in range(11)]
    return c


def _avg_goal_diff(home_fam, away_fam, n=2000):
    total = 0
    for s in range(n):
        m = simulate_match(_club(1), _club(2), new_rng(s), home_fam, away_fam)
        total += m.home_goals - m.away_goals
    return total / n


def test_familiarity_effect_helps_the_better_trained():
    even = _avg_goal_diff(50, 50)
    trained = _avg_goal_diff(100, 20)      # local mucho mejor entrenado
    untrained = _avg_goal_diff(20, 100)    # local mucho peor entrenado
    assert trained > even > untrained      # la familiaridad inclina el resultado


def test_simulate_match_defaults_are_neutral():
    # Sin pasar familiaridad, el resultado es el de siempre (50 = neutro).
    a = simulate_match(_club(1), _club(2), new_rng(5))
    b = simulate_match(_club(1), _club(2), new_rng(5), 50.0, 50.0)
    assert (a.home_goals, a.away_goals) == (b.home_goals, b.away_goals)


def test_train_formation_raises_level_and_best():
    club = _club()
    ft.ensure_all(club)
    name = "4-3-3"
    before = ft.training_level(club, name)
    ft.train_formation(club, name, None)
    after = ft.training_level(club, name)
    assert after > before                                  # jugar sube la familiaridad
    assert ft.best_familiarity(club) >= after              # la mejor incluye a esta
