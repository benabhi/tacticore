"""Tests del modelo de jugador y su generador."""

from tacticore.core.rng import new_rng
from tacticore.domain.enums import Position
from tacticore.generators import PlayerGenerator

_SKILLS = (
    "goalkeeping", "defending", "playmaking", "winger", "passing", "scoring",
    "set_pieces", "stamina", "experience", "leadership",
)


def test_generated_player_is_deterministic():
    a = PlayerGenerator(new_rng(1)).generate(Position.FORWARD)
    b = PlayerGenerator(new_rng(1)).generate(Position.FORWARD)
    assert a == b


def test_skills_in_valid_range():
    player = PlayerGenerator(new_rng(3)).generate()
    for skill in _SKILLS:
        value = getattr(player, skill)
        assert 1 <= value <= 20, f"{skill}={value} fuera de 1-20"
    assert 1 <= player.overall <= 20


def test_goalkeeper_profile():
    # Un arquero debe tener goalkeeping alto comparado con scoring.
    gk = PlayerGenerator(new_rng(5)).generate(Position.GOALKEEPER)
    assert gk.goalkeeping >= 10
    assert gk.goalkeeping > gk.scoring


def test_display_name_prefers_nickname():
    player = PlayerGenerator(new_rng(2)).generate()
    player.nickname = "La Pulga"
    assert player.display_name == "La Pulga"
    player.nickname = None
    assert player.display_name == player.full_name
