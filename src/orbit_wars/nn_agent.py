"""orbit-wars NN policy 推論 wrapper (Phase 0.2)。

役割:
  - torch.nn モデルを load → kaggle_environments style の `agent(observation, configuration)`
    callable に wrap
  - state encoding (encoders.py) → forward → action decode → action list の pipeline
  - action masking: 自分の planet 以外の home output は無視、
    capacity 超え ships は clamp、太陽通過 (forbidden cone) は safe_angle_around で回避

提出 (Kaggle submit) との互換性:
  - kaggle eval では `agent.py` が標準入出力 single-file 制約。`make submit-tar` で
    tar 化すれば multi-file 可能 (= weights .pt + helper モジュール一緒に upload)
  - submit 時は agents/proxy/<name>.py が `make_nn_agent('weights.pt')` を呼んで
    `agent` を module top-level に export する
"""

from __future__ import annotations

from pathlib import Path

import torch
import torch.nn as nn

try:
    from . import physics
    from .encoders import (
        MAX_PLANETS,
        PER_HOME_ACTIONS,
        STATE_DIM,
        decode_action,
        encode_state,
    )
except (ImportError, KeyError):
    import physics  # type: ignore[no-redef]
    from encoders import (  # type: ignore[no-redef]
        MAX_PLANETS,
        PER_HOME_ACTIONS,
        STATE_DIM,
        decode_action,
        encode_state,
    )


# ============================================================================
# Model architecture
# ============================================================================


class SimpleMLPPolicy(nn.Module):
    """state vector → per-home action logits の単純 MLP。

    BC training (Phase 0.4) と PPO finetune (Phase 2 候補 A) の両方で使える基底。
    後で SE-ResNet / Transformer に置き換え可能 (= save/load の interface 互換)。
    """

    def __init__(
        self,
        state_dim: int = STATE_DIM,
        hidden_dims: tuple[int, ...] = (512, 256),
        n_homes: int = MAX_PLANETS,
        n_actions: int = PER_HOME_ACTIONS,
    ):
        super().__init__()
        layers: list[nn.Module] = []
        prev = state_dim
        for h in hidden_dims:
            layers.append(nn.Linear(prev, h))
            layers.append(nn.ReLU())
            prev = h
        layers.append(nn.Linear(prev, n_homes * n_actions))
        self.net = nn.Sequential(*layers)
        self.n_homes = n_homes
        self.n_actions = n_actions

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (B, state_dim)
        Returns:
            logits: (B, n_homes, n_actions)
        """
        out = self.net(x)
        return out.view(-1, self.n_homes, self.n_actions)


# ============================================================================
# Inference helpers
# ============================================================================


def _home_capacity(ships: int, max_fraction: float = 0.85, reserve: int = 5) -> int:
    """CaptureMission と同じ capacity 計算 (= 守備兵力を残す)."""
    return max(0, min(int(ships * max_fraction), ships - reserve))


def make_nn_agent(
    model_path: str | Path,
    device: str = "cpu",
    sun_safety_margin_rad: float = 0.035,  # ~ 2°
    suppress_no_op: bool = False,
):
    """提出可能な agent function を返す。kaggle_environments 互換。

    Args:
        model_path: 学習済 .pt の path (state_dict format)。
        device: 'cpu' or 'cuda'.
        sun_safety_margin_rad: 太陽 forbidden cone 回避マージン (radians).
        suppress_no_op: True なら inference 時に NO_OP_CLASS の logit を -inf にして
            必ず fire class を選ばせる。BC pretrain で no-op majority bias に陥った
            policy の hack 修正用。capacity 不足の場合は decode_action が None を
            返すので natural に skip される。

    Returns:
        agent(observation, configuration) callable.
    """
    model = SimpleMLPPolicy()
    state_dict = torch.load(model_path, map_location=device, weights_only=True)
    model.load_state_dict(state_dict)
    model.eval()
    model.to(device)

    def agent(observation, configuration=None):
        try:
            enc = encode_state(observation)
            if not enc.my_planet_ids:
                return []
            x = torch.from_numpy(enc.state_vec).unsqueeze(0).to(device)
            with torch.no_grad():
                logits = model(x).squeeze(0)  # (n_homes, n_actions)

            actions: list[list[float]] = []
            planets_dict = {int(p[0]): p for p in observation.get("planets", [])}
            player = int(observation.get("player", 0) or 0)

            for idx, pid in enumerate(enc.my_planet_ids):
                if idx >= MAX_PLANETS:
                    break
                planet = planets_dict.get(pid)
                if planet is None or int(planet[1]) != player:
                    continue
                home_ships = int(planet[5])
                home_cap = _home_capacity(home_ships)
                if home_cap <= 0:
                    continue
                # mask: capacity 超え class を suppress
                pred_logits = logits[idx].clone()
                # 簡易 capacity mask: ship_fraction bin が大きすぎる class を down-weight
                # (詳細 mask は後で改善)
                if suppress_no_op:
                    pred_logits[0] = float("-inf")  # NO_OP_CLASS=0 を抑制
                pred = int(pred_logits.argmax().item())
                decoded = decode_action(pred, home_cap)
                if decoded is None:
                    continue
                angle, ships = decoded
                if ships <= 0 or ships > home_cap:
                    continue
                # 太陽 forbidden cone を回避
                home_x, home_y = float(planet[2]), float(planet[3])
                safe = physics.safe_angle_around(
                    home_x, home_y, angle, margin=sun_safety_margin_rad
                )
                actions.append([float(pid), float(safe), int(ships)])
            return actions
        except Exception:
            # 万一の例外は空 action で safe-fail (= timeout 回避)
            return []

    return agent


def save_random_init(output_path: str | Path) -> None:
    """random 初期化された SimpleMLPPolicy を save する (smoke test 用)."""
    model = SimpleMLPPolicy()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), output_path)
