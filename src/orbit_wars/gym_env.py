"""orbit-wars Gymnasium wrapper for PPO/RL training (Phase 2 候補 A)。

kaggle_environments の orbit_wars を **single-agent gymnasium.Env** 風に wrap する。
opponent agent は外部から callable で渡す (= self-play / heuristic / IL fixed)。

設計:
    - obs: encoders.encode_state の flat vector (STATE_DIM dim)
    - action: MultiDiscrete([PER_HOME_ACTIONS] * MAX_PLANETS)
              各 home について {NO_OP, fire(angle, fraction)} の class id
    - reward:
        - terminal: 勝者 +1, 敗者 -1, draw 0
        - shaped: ship_share delta per turn (= 自陣 ships / 全 ships の variation)
    - episode terminates: orbit-wars 環境が done を返した時 (= step >= 500 or 0 planet)
    - opponent: 任意の callable `agent(observation, configuration) -> action_list`
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces

try:
    from . import physics
    from .encoders import (
        MAX_PLANETS,
        NO_OP_CLASS,
        PER_HOME_ACTIONS,
        STATE_DIM,
        decode_action,
        encode_state,
    )
except (ImportError, KeyError):
    import physics  # type: ignore[no-redef]
    from encoders import (  # type: ignore[no-redef]
        MAX_PLANETS,
        NO_OP_CLASS,
        PER_HOME_ACTIONS,
        STATE_DIM,
        decode_action,
        encode_state,
    )


def _home_capacity(ships: int, max_fraction: float = 0.85, reserve: int = 5) -> int:
    return max(0, min(int(ships * max_fraction), ships - reserve))


def _decode_action_array(
    action_arr: np.ndarray,
    obs: dict,
    my_planet_ids: list[int],
    sun_safety_margin_rad: float = 0.035,
) -> list[list[float]]:
    """numpy class id array → kaggle action list."""
    actions: list[list[float]] = []
    planets_dict = {int(p[0]): p for p in obs.get("planets", [])}
    for idx, pid in enumerate(my_planet_ids):
        if idx >= len(action_arr) or idx >= MAX_PLANETS:
            break
        cls = int(action_arr[idx])
        if cls == NO_OP_CLASS:
            continue
        planet = planets_dict.get(pid)
        if planet is None:
            continue
        home_cap = _home_capacity(int(planet[5]))
        if home_cap <= 0:
            continue
        decoded = decode_action(cls, home_cap)
        if decoded is None:
            continue
        angle, ships = decoded
        if ships <= 0 or ships > home_cap:
            continue
        home_x, home_y = float(planet[2]), float(planet[3])
        safe = physics.safe_angle_around(home_x, home_y, angle, margin=sun_safety_margin_rad)
        actions.append([float(pid), float(safe), int(ships)])
    return actions


class OrbitWarsEnv(gym.Env):
    """Gymnasium wrapper for kaggle_environments orbit_wars (player 0 視点)."""

    metadata = {"render_modes": []}

    def __init__(
        self,
        opponent_fn: Callable[[dict, Any], list],
        seed: int | None = None,
        shaped_reward_weight: float = 0.0,
        my_player: int = 0,
    ):
        super().__init__()
        self.opponent_fn = opponent_fn
        self._seed = seed
        self.shaped_reward_weight = shaped_reward_weight
        self.my_player = my_player

        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(STATE_DIM,), dtype=np.float32
        )
        self.action_space = spaces.MultiDiscrete([PER_HOME_ACTIONS] * MAX_PLANETS)

        # lazy init kaggle env (required since kaggle_environments uses singletons)
        from kaggle_environments import make as _make

        cfg = {"seed": seed} if seed is not None else {}
        self._kenv = _make("orbit_wars", configuration=cfg, debug=False)
        self._last_my_share: float = 0.5
        self._last_my_planet_ids: list[int] = []

    def _my_obs(self) -> dict:
        if self._kenv.done:
            return self._kenv.steps[-1][self.my_player].get("observation") or {}
        return self._kenv.state[self.my_player].get("observation") or {}

    def _opp_obs(self) -> dict:
        opp_idx = 1 - self.my_player
        if self._kenv.done:
            return self._kenv.steps[-1][opp_idx].get("observation") or {}
        return self._kenv.state[opp_idx].get("observation") or {}

    def _ship_share(self, obs: dict) -> float:
        """自陣 ships / 全 ships 比 (= 0-1)."""
        planets = obs.get("planets") or []
        fleets = obs.get("fleets") or []
        my, total = 0, 0
        for p in planets:
            ships = int(p[5])
            total += ships
            if int(p[1]) == self.my_player:
                my += ships
        for f in fleets:
            ships = int(f[6])
            total += ships
            if int(f[1]) == self.my_player:
                my += ships
        return my / max(total, 1)

    def reset(self, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        if seed is None:
            seed = self._seed
        from kaggle_environments import make as _make

        cfg = {"seed": seed} if seed is not None else {}
        self._kenv = _make("orbit_wars", configuration=cfg, debug=False)
        self._kenv.reset()

        obs = self._my_obs()
        enc = encode_state(obs, player=self.my_player)
        self._last_my_planet_ids = enc.my_planet_ids
        self._last_my_share = self._ship_share(obs)
        return enc.state_vec, {}

    def step(self, action: np.ndarray):
        # 1. decode my action with current my_planet_ids
        my_obs = self._my_obs()
        enc = encode_state(my_obs, player=self.my_player)
        my_actions = _decode_action_array(np.asarray(action), my_obs, enc.my_planet_ids)

        # 2. opponent action
        opp_obs = self._opp_obs()
        try:
            opp_actions = self.opponent_fn(opp_obs, None)
        except Exception:
            opp_actions = []

        # 3. step kaggle env
        if self.my_player == 0:
            step_actions = [my_actions, opp_actions]
        else:
            step_actions = [opp_actions, my_actions]
        self._kenv.step(step_actions)

        # 4. compute reward
        new_obs = self._my_obs()
        new_share = self._ship_share(new_obs)
        shaped = self.shaped_reward_weight * (new_share - self._last_my_share)
        self._last_my_share = new_share

        terminated = bool(self._kenv.done)
        terminal_reward = 0.0
        if terminated:
            r = self._kenv.steps[-1][self.my_player].get("reward")
            terminal_reward = float(r) if r is not None else 0.0
        reward = terminal_reward + shaped

        # 5. next obs
        new_enc = encode_state(new_obs, player=self.my_player)
        return (
            new_enc.state_vec,
            float(reward),
            terminated,
            False,  # truncated (we don't truncate explicitly, kaggle does)
            {"my_planet_ids": new_enc.my_planet_ids},
        )

    def close(self):
        pass
