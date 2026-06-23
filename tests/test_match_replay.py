"""Tests de replay: seed + cola de comandos -> partido reproducible (B4)."""

import pytest

from tacticore.core.rng import new_rng
from tacticore.domain.enums import LeagueTier
from tacticore.generators import ClubGenerator
from tacticore.simulation.match import (
    MatchEngine,
    SetPlayerZone,
    Side,
    Vec2,
    kickoff_state,
)


def _fresh_state():
    gen = ClubGenerator(new_rng(42))
    home = gen.generate(squad_size=16, country_code="AR", tier=LeagueTier.C)
    away = gen.generate(squad_size=16, country_code="BR", tier=LeagueTier.C)
    return kickoff_state(home, away)


def _snapshot(engine):
    """Foto comparable del partido: posiciones, pelota y marcador."""
    players = [(round(mp.position.x, 6), round(mp.position.y, 6))
               for mp in engine.state.all_players()]
    ball = (engine.state.ball.position.x, engine.state.ball.position.y)
    score = (engine.state.score_home, engine.state.score_away)
    return players, ball, score


def test_command_takes_effect():
    state = _fresh_state()
    cmd = SetPlayerZone(tick=10, side=Side.HOME, player_index=3, zone=Vec2(70.0, 12.0))
    engine = MatchEngine(state, new_rng(5), commands=[cmd])
    engine.run(1.0)  # 30 ticks > 10
    assert state.home[3].base_position == Vec2(70.0, 12.0)


def test_commands_change_the_match():
    plain = MatchEngine(_fresh_state(), new_rng(5))
    plain.run(4.0)
    # Movemos a un defensor (sostiene su zona) a una zona muy distinta.
    cmd = SetPlayerZone(tick=10, side=Side.HOME, player_index=1, zone=Vec2(90.0, 60.0))
    altered = MatchEngine(_fresh_state(), new_rng(5), commands=[cmd])
    altered.run(4.0)
    # La orden del manager cambia el desarrollo del partido.
    assert _snapshot(plain) != _snapshot(altered)
    assert plain.state.home[1].position != altered.state.home[1].position


def test_replay_is_identical():
    log = [
        SetPlayerZone(tick=15, side=Side.HOME, player_index=2, zone=Vec2(60.0, 10.0)),
        SetPlayerZone(tick=60, side=Side.AWAY, player_index=3, zone=Vec2(45.0, 58.0)),
    ]
    a = MatchEngine(_fresh_state(), new_rng(7), commands=list(log))
    b = MatchEngine(_fresh_state(), new_rng(7), commands=list(log))
    a.run(8.0)
    b.run(8.0)
    assert _snapshot(a) == _snapshot(b)


def test_live_commands_can_be_replayed():
    # "En vivo": vamos pisando ticks y, en el medio, el manager da una orden.
    live = MatchEngine(_fresh_state(), new_rng(3))
    for t in range(180):
        if t == 40:
            live.schedule(
                SetPlayerZone(tick=40, side=Side.HOME, player_index=5, zone=Vec2(75.0, 30.0))
            )
        if t == 120:
            live.schedule(
                SetPlayerZone(tick=120, side=Side.AWAY, player_index=1, zone=Vec2(30.0, 40.0))
            )
        live.step()

    # Replay: misma seed + el log grabado -> partido identico.
    replay = MatchEngine(_fresh_state(), new_rng(3), commands=list(live.command_log))
    for _ in range(180):
        replay.step()

    assert _snapshot(live) == _snapshot(replay)


def test_schedule_in_the_past_raises():
    engine = MatchEngine(_fresh_state(), new_rng(1))
    engine.run(1.0)  # va por el tick 30
    with pytest.raises(ValueError):
        engine.schedule(SetPlayerZone(tick=5, side=Side.HOME, player_index=0, zone=Vec2(1.0, 1.0)))
