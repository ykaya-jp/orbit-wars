"""orbit_wars.nn_agent + encoders の smoke test."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import torch

from orbit_wars.encoders import (
    MAX_PLANETS,
    NO_OP_CLASS,
    PER_HOME_ACTIONS,
    STATE_DIM,
    decode_action,
    encode_action,
    encode_state,
)
from orbit_wars.nn_agent import SimpleMLPPolicy, make_nn_agent, save_random_init

# ============================================================================
# encode_state
# ============================================================================


class TestEncodeState:
    def test_empty_observation(self):
        obs = {"player": 0, "planets": [], "fleets": [], "step": 0}
        enc = encode_state(obs)
        assert enc.state_vec.shape == (STATE_DIM,)
        assert enc.state_vec.dtype == np.float32
        assert enc.my_planet_ids == []

    def test_basic_state(self):
        obs = {
            "player": 0,
            "step": 10,
            "angular_velocity": 0.04,
            "planets": [
                [0, 0, 75, 75, 1.5, 100, 3],  # mine
                [1, 1, 25, 25, 1.5, 50, 2],  # enemy
                [2, -1, 50, 80, 1.0, 5, 1],  # neutral
            ],
            "fleets": [
                [0, 0, 60, 60, 0.5, 0, 50],  # mine
                [1, 1, 40, 40, 1.0, 1, 30],  # enemy
            ],
            "comet_planet_ids": [],
        }
        enc = encode_state(obs)
        assert enc.state_vec.shape == (STATE_DIM,)
        assert enc.my_planet_ids == [0]

    def test_player_id_filter(self):
        # owner=1 を player=1 から見ると "mine"
        obs = {
            "player": 1,
            "planets": [[0, 1, 75, 75, 1.5, 100, 3]],
        }
        enc = encode_state(obs, player=1)
        assert enc.my_planet_ids == [0]


# ============================================================================
# encode_action / decode_action
# ============================================================================


class TestActionEncoding:
    def test_no_op(self):
        labels = encode_action([], my_planet_ids=[0, 1])
        assert labels.shape == (MAX_PLANETS,)
        assert (labels == 0).all()

    def test_single_launch(self):
        # angle=0 (= +x 方向)、ships=20 (= bin 1)
        labels = encode_action([[0, 0.0, 20]], my_planet_ids=[0, 1])
        # planet 0 → index 0
        # angle 0 (radians) は bin 0 (= [0, 22.5°))
        # ships 20 は bin 1 (10-29)
        # cls = 1 + 0*5 + 1 = 2
        assert labels[0] == 2
        assert labels[1] == 0

    def test_multi_launch_keeps_first(self):
        # 2 launch from same home → 1 つ目のみ採用
        labels = encode_action([[0, 0.0, 20], [0, math.pi, 50]], my_planet_ids=[0])
        # 1 つ目 (angle=0, ships=20, bin 0/1) のみ → cls = 2
        assert labels[0] == 2

    def test_decode_no_op(self):
        assert decode_action(NO_OP_CLASS, home_capacity=10) is None

    def test_decode_round_trip(self):
        # encode → decode で angle/ships が roughly 一致
        labels = encode_action([[0, math.pi / 4, 60]], my_planet_ids=[0])
        cls = int(labels[0])
        decoded = decode_action(cls, home_capacity=200)
        assert decoded is not None
        angle, ships = decoded
        # angle: π/4 (= 45°) → bin 2 (= [45°, 67.5°)) → center 56.25°
        # bin 2 center radians = (2 + 0.5) * 2π/16 = 2.5 * π/8 = 5π/16 ≈ 0.982
        # 入力 π/4 ≈ 0.785。bin center は 0.982 で誤差 0.2。bin 幅 π/8 = 0.39 内
        assert abs(angle - 5 * math.pi / 16) < 0.05
        # ships 60 は bin 2 (30-99) → frac_bin=2 → ships = 60 (decode の中央値)
        assert ships == 60


# ============================================================================
# SimpleMLPPolicy + make_nn_agent
# ============================================================================


class TestNNAgent:
    def test_model_forward_shape(self):
        model = SimpleMLPPolicy()
        x = torch.zeros(4, STATE_DIM)
        logits = model(x)
        assert logits.shape == (4, MAX_PLANETS, PER_HOME_ACTIONS)

    def test_save_and_load_random(self, tmp_path: Path):
        weights = tmp_path / "test.pt"
        save_random_init(weights)
        assert weights.exists()
        agent = make_nn_agent(weights, device="cpu")
        # call agent on minimal observation
        obs = {
            "player": 0,
            "step": 5,
            "angular_velocity": 0.04,
            "planets": [
                [0, 0, 75, 75, 1.5, 100, 3],
                [1, -1, 60, 60, 1.0, 5, 2],
            ],
            "fleets": [],
            "comet_planet_ids": [],
        }
        actions = agent(obs)
        # actions は list (空 or [[from_id, angle, ships], ...])
        assert isinstance(actions, list)
        for a in actions:
            assert len(a) == 3
            assert isinstance(a[2], int)
            # ship count is positive
            assert a[2] > 0
            # angle is finite
            assert math.isfinite(a[1])

    def test_agent_safe_on_exception(self, tmp_path: Path):
        # 不正な observation でも空 list を返す
        weights = tmp_path / "test.pt"
        save_random_init(weights)
        agent = make_nn_agent(weights, device="cpu")
        # observation = None
        actions = agent(None)
        assert actions == []
