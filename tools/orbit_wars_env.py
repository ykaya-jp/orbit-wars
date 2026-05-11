"""Gymnasium-compatible OrbitWars 4P FFA environment wrapper for PPO.

Player 0 = our agent (= the one being trained).
Players 1, 2, 3 = opponent callables (rule-base / IL / self-history).

State (per step, observed by player 0):
    spatial: (14, 64, 64) float32 — encode_grid_state output
    globals: (9,) float32 — global features

Action:
    Per my_planet, an integer in [0, 81): 0 = no_op, 1-80 = (angle_bin × 5 + frac_bin) + 1.
    But to keep action space fixed-size per env step, we use **flat (64*64,) action**:
    each cell selects one of 81 classes; cells without my_planet are masked at decode time.

    For PPO simplicity here, we use a single "primary action" interface:
    action = int in [0, 64*64*81) — quotient/remainder decode → (cell_id, action_class).
    The wrapper picks the cell-action with highest probability for each my_planet.

    Actually for cleaner gym Box compatibility, action = (64*64, 81) flat probs from policy,
    decoded server-side. But gym requires Discrete or MultiDiscrete. We use MultiDiscrete
    of size [81] * MAX_PLANETS where MAX_PLANETS = 30 (orbit_wars has < 30 planets per game).

Reward:
    Per step: 0 (no shaping at first; can add ship/planet delta shaping later)
    Terminal: rank-based {1: +1.0, 2: +0.3, 3: -0.3, 4: -1.0}

Done:
    Episode end (= 500 steps or all opponents eliminated)
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

import gymnasium as gym
import numpy as np
from gymnasium import spaces

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from orbit_wars.grid_encoder import (  # noqa: E402
    GLOBAL_FEAT_DIM,
    GRID_SIZE,
    N_CHANNELS,
    PER_CELL_ACTIONS,
    encode_grid_state,
)

MAX_MY_PLANETS = 30  # orbit_wars max is around 24-30 per game


class OrbitWarsEnv(gym.Env):
    """Gymnasium env for OrbitWars 4P FFA, single-agent perspective (player 0)."""

    metadata = {"render_modes": []}

    def __init__(
        self,
        opponents: list[Callable],
        seed: int | None = None,
        episode_steps: int = 500,
        agent_timeout: float = 2.0,
        terminal_reward_only: bool = True,
        ship_delta_weight: float = 0.001,
        planet_delta_weight: float = 0.01,
    ):
        super().__init__()
        assert len(opponents) == 3, f"need 3 opponents for 4P, got {len(opponents)}"
        self.opponents = opponents
        self.episode_steps = episode_steps
        self.agent_timeout = agent_timeout
        self.terminal_reward_only = terminal_reward_only
        self.ship_delta_weight = ship_delta_weight
        self.planet_delta_weight = planet_delta_weight
        self._seed = seed

        # Observation: spatial + globals concatenated as Dict
        self.observation_space = spaces.Dict(
            {
                "spatial": spaces.Box(
                    low=-10.0, high=10.0, shape=(N_CHANNELS, GRID_SIZE, GRID_SIZE), dtype=np.float32
                ),
                "globals": spaces.Box(
                    low=-10.0, high=10.0, shape=(GLOBAL_FEAT_DIM,), dtype=np.float32
                ),
                # action_mask: 1.0 for cells with my_planet, 0.0 otherwise
                "action_mask": spaces.Box(
                    low=0.0, high=1.0, shape=(GRID_SIZE * GRID_SIZE,), dtype=np.float32
                ),
            }
        )

        # Action: per-cell class (we flatten to single Discrete + cell_id later)
        # For simplicity start with: action = int in [0, GRID_SIZE * GRID_SIZE * PER_CELL_ACTIONS)
        # = (cell_id * 81) + class. Decoder: cell_id, class = divmod(a, 81)
        # Take **single action per env step** (= top-1 my_planet by ships chooses one move)
        # Multi-planet support: we'll need MultiBinary or sequential. For PPO simplicity
        # start with: predict for ONE designated cell per step (= largest my_planet).
        self.action_space = spaces.Discrete(GRID_SIZE * GRID_SIZE * PER_CELL_ACTIONS)

        self.kaggle_env = None
        self._step_count = 0
        self._prev_my_ships = 0
        self._prev_my_planets = 0

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        from kaggle_environments import make

        config = {"episodeSteps": self.episode_steps, "agentTimeout": self.agent_timeout}
        if seed is not None:
            config["seed"] = seed
        elif self._seed is not None:
            config["seed"] = self._seed

        self.kaggle_env = make("orbit_wars", configuration=config, debug=False)
        self.kaggle_env.reset(num_agents=4)
        self._step_count = 0

        obs0 = self._get_obs0()
        encoded = self._encode(obs0)
        self._prev_my_ships = self._sum_my_ships(obs0)
        self._prev_my_planets = self._count_my_planets(obs0)

        return encoded, {}

    def step(self, action: int):
        """One env step. Action = int decoded to (cell_id, class)."""
        # Decode action
        cell_id, action_class = divmod(int(action), PER_CELL_ACTIONS)
        row, col = divmod(cell_id, GRID_SIZE)

        # Build my actions list: pick the my_planet at (row, col) and apply the decoded class
        my_actions = self._build_my_actions(row, col, action_class)

        # Get opponent actions
        all_states = self.kaggle_env.steps[-1]
        opp_actions: list = [my_actions]  # player 0 = us
        for i, opp_fn in enumerate(self.opponents, start=1):
            try:
                opp_obs = all_states[i].observation
                a = opp_fn(opp_obs)
            except Exception:
                a = []
            opp_actions.append(a)

        # Kaggle step
        self.kaggle_env.step(opp_actions)
        self._step_count += 1

        new_states = self.kaggle_env.steps[-1]
        obs0 = new_states[0].observation
        encoded = self._encode(obs0)

        # Compute reward
        reward = 0.0
        done = self.kaggle_env.done
        if not self.terminal_reward_only:
            cur_ships = self._sum_my_ships(obs0)
            cur_planets = self._count_my_planets(obs0)
            reward += self.ship_delta_weight * (cur_ships - self._prev_my_ships)
            reward += self.planet_delta_weight * (cur_planets - self._prev_my_planets)
            self._prev_my_ships = cur_ships
            self._prev_my_planets = cur_planets

        if done:
            # Terminal rank-based reward
            rewards = [s.reward if s.reward is not None else 0.0 for s in new_states]
            # rank: 1st = +1.0, 2nd = +0.3, 3rd = -0.3, 4th = -1.0
            sorted_rewards = sorted(enumerate(rewards), key=lambda x: -x[1])
            rank_map = {1: 1.0, 2: 0.3, 3: -0.3, 4: -1.0}
            for rank, (player_idx, _) in enumerate(sorted_rewards, start=1):
                if player_idx == 0:
                    reward += rank_map[rank]
                    break

        truncated = False
        return encoded, reward, done, truncated, {}

    def _get_obs0(self):
        return self.kaggle_env.steps[-1][0].observation

    def _encode(self, obs0):
        obs_with_player = dict(obs0)
        obs_with_player.setdefault("player", 0)
        try:
            enc = encode_grid_state(obs_with_player, player=0)
        except Exception:
            return {
                "spatial": np.zeros((N_CHANNELS, GRID_SIZE, GRID_SIZE), dtype=np.float32),
                "globals": np.zeros((GLOBAL_FEAT_DIM,), dtype=np.float32),
                "action_mask": np.zeros((GRID_SIZE * GRID_SIZE,), dtype=np.float32),
            }

        mask = np.zeros((GRID_SIZE * GRID_SIZE,), dtype=np.float32)
        for _pid, r, c in enc.my_cells:
            mask[r * GRID_SIZE + c] = 1.0

        return {
            "spatial": enc.spatial.astype(np.float32),
            "globals": enc.globals_.astype(np.float32),
            "action_mask": mask,
        }

    def _build_my_actions(self, row: int, col: int, action_class: int) -> list:
        """Convert (row, col, action_class) to kaggle_environments action format."""
        if action_class == 0:  # no_op
            return []
        obs0 = self._get_obs0()
        planets = obs0.get("planets", [])
        # Find my_planet at this cell
        from orbit_wars.grid_encoder import _board_to_cell

        target_pid = None
        target_planet = None
        for p in planets:
            if int(p[1]) != 0:  # not mine
                continue
            r, c = _board_to_cell(float(p[2]), float(p[3]))
            if r == row and c == col:
                target_pid = int(p[0])
                target_planet = p
                break
        if target_pid is None:
            return []  # invalid cell, no-op

        # Decode action_class to (angle, ships)
        import math as _math

        from orbit_wars.grid_encoder import ANGLE_BINS, SHIP_FRAC_BINS

        cls = action_class - 1
        angle_bin = cls // SHIP_FRAC_BINS
        frac_bin = cls % SHIP_FRAC_BINS
        angle = (angle_bin + 0.5) * (2 * _math.pi / ANGLE_BINS)
        if angle > _math.pi:
            angle -= 2 * _math.pi
        frac_to_ships = {0: 5, 1: 20, 2: 60, 3: 200, 4: 500}
        home_ships = int(target_planet[5])
        max_send = max(0, min(int(home_ships * 0.85), home_ships - 5))
        ships = min(frac_to_ships.get(frac_bin, 5), max_send)
        if ships <= 0:
            return []
        return [[float(target_pid), float(angle), int(ships)]]

    def _sum_my_ships(self, obs0) -> int:
        return sum(int(p[5]) for p in obs0.get("planets", []) if int(p[1]) == 0)

    def _count_my_planets(self, obs0) -> int:
        return sum(1 for p in obs0.get("planets", []) if int(p[1]) == 0)
