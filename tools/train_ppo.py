"""PPO training for OrbitWars (Phase θ).

Uses MaskablePPO from sb3-contrib with custom feature extractor based on
GridSEResNet backbone.

Curriculum:
  θ.1: vs 3 random opponents (= basic firing learn)
  θ.2: vs Marco/orbitbotnext mix
  θ.3: vs konbu17/Rudra/zachary mix
  θ.4: self-play (PFSP)

Usage:
    python -m tools.train_ppo --total-timesteps 100000 --output agents/proxy/ppo_v1.zip
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from sb3_contrib import MaskablePPO
from sb3_contrib.common.maskable.policies import MaskableMultiInputActorCriticPolicy
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from stable_baselines3.common.vec_env import DummyVecEnv

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))
_SRC = _TOOLS.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from orbit_wars_env import OrbitWarsEnv  # noqa: E402

from orbit_wars.grid_encoder import (  # noqa: E402
    GLOBAL_FEAT_DIM,
    GRID_SIZE,
    N_CHANNELS,
    PER_CELL_ACTIONS,
)
from orbit_wars.grid_model import GridSEResNet  # noqa: E402


class GridFeatureExtractor(BaseFeaturesExtractor):
    """Spatial features (GridSEResNet backbone) + globals → fixed-size feature."""

    def __init__(self, observation_space, features_dim: int = 256):
        super().__init__(observation_space, features_dim=features_dim)
        self.backbone = GridSEResNet(
            in_channels=N_CHANNELS,
            base_channels=32,
            n_blocks=4,
            global_feat_dim=GLOBAL_FEAT_DIM,
        )
        self.proj = nn.Sequential(
            nn.Linear(32 + GLOBAL_FEAT_DIM, 128),
            nn.ReLU(inplace=True),
            nn.Linear(128, features_dim),
            nn.ReLU(inplace=True),
        )

    def forward(self, observations: dict) -> torch.Tensor:
        spatial = observations["spatial"]
        globals_ = observations["globals"]
        x = self.backbone.stem(spatial)
        x = self.backbone.blocks(x)  # (B, 32, H, W)
        mask = observations["action_mask"]
        mask_2d = mask.view(-1, GRID_SIZE, GRID_SIZE).unsqueeze(1)
        masked = x * mask_2d
        spatial_pool = masked.sum(dim=(2, 3)) / (mask_2d.sum(dim=(2, 3)) + 1e-6)
        feat = torch.cat([spatial_pool, globals_], dim=1)
        return self.proj(feat)


def make_random_opponent():
    def random_agent(obs):
        return []

    return random_agent


def make_file_opponent(path: str):
    """Load an agent from a .py file as opponent (= for curriculum mix)."""
    import importlib.util
    import sys as _sys

    mod_name = f"_opp_{Path(path).stem}_{abs(hash(path)) % 100000}"
    spec = importlib.util.spec_from_file_location(mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    _sys.modules[mod_name] = mod  # required for dataclasses inside the module
    spec.loader.exec_module(mod)
    return mod.agent


def mask_fn(env) -> np.ndarray:
    """Per-cell × per-action mask (= 4096×81 = 331776 bool)."""
    inner = env
    while hasattr(inner, "env") and not isinstance(inner, OrbitWarsEnv):
        inner = inner.env
    obs = inner._encode(inner._get_obs0())
    cell_mask = obs["action_mask"]
    full = np.repeat(cell_mask, PER_CELL_ACTIONS)
    # Guarantee at least one action available: action 0 = (cell 0, class 0) = no-op
    full[0] = 1.0
    return full.astype(bool)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--total-timesteps", type=int, default=10000)
    ap.add_argument("--n-envs", type=int, default=1)
    ap.add_argument("--learning-rate", type=float, default=3e-4)
    ap.add_argument("--n-steps", type=int, default=256)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--n-epochs", type=int, default=4)
    ap.add_argument("--gamma", type=float, default=0.997)
    ap.add_argument("--gae-lambda", type=float, default=0.95)
    ap.add_argument("--ent-coef", type=float, default=0.01)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--output", default="agents/proxy/ppo_v1.zip")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--reward-shaping", action="store_true", help="enable step-wise rewards")
    ap.add_argument(
        "--opponents",
        nargs="+",
        default=["random"],
        help="opponent specs: 'random' or path to .py with `agent` function. "
        "If <3 specs given, randomly sample to fill 3 opponent slots per env.",
    )
    args = ap.parse_args()

    print(f"PPO: {args.total_timesteps} steps, {args.n_envs} envs, device={args.device}")
    print(f"  opponents pool: {args.opponents}")

    # Pre-load opponent functions
    opponent_pool: list = []
    for spec in args.opponents:
        if spec == "random":
            opponent_pool.append(("random", None))
        else:
            opponent_pool.append((spec, make_file_opponent(spec)))

    def sample_opponents() -> list:
        """Sample 3 opponents from pool (with replacement if pool < 3)."""
        import random as _random

        sampled = _random.choices(opponent_pool, k=3)
        return [make_random_opponent() if name == "random" else fn for name, fn in sampled]

    def env_factory(rank: int):
        def _f():
            env = OrbitWarsEnv(
                opponents=sample_opponents(),
                seed=args.seed + rank * 1000,
                episode_steps=500,
                terminal_reward_only=not args.reward_shaping,
            )
            env = ActionMasker(env, mask_fn)
            return env

        return _f

    venv = DummyVecEnv([env_factory(i) for i in range(args.n_envs)])

    policy_kwargs = dict(
        features_extractor_class=GridFeatureExtractor,
        features_extractor_kwargs=dict(features_dim=256),
        net_arch=dict(pi=[128], vf=[128]),
    )

    model = MaskablePPO(
        MaskableMultiInputActorCriticPolicy,
        venv,
        learning_rate=args.learning_rate,
        n_steps=args.n_steps,
        batch_size=args.batch_size,
        n_epochs=args.n_epochs,
        gamma=args.gamma,
        gae_lambda=args.gae_lambda,
        ent_coef=args.ent_coef,
        policy_kwargs=policy_kwargs,
        device=args.device,
        verbose=1,
        seed=args.seed,
    )

    n_params = sum(p.numel() for p in model.policy.parameters())
    print(f"params: {n_params:,}")
    model.learn(total_timesteps=args.total_timesteps, progress_bar=False)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(str(out_path))
    print(f"saved: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
