"""PPO self-play / vs-heuristic training (Phase 2 候補 A pilot)。

stable-baselines3 PPO + OrbitWarsEnv で agent を learn する。Halite IV ttvand /
Lux S3 Frog Parade の歴史的レシピ準拠だが、超簡易版 (1-day pilot 用)。

curriculum (適用順):
    1. vs random        (~50k steps)  — 基本動作習得
    2. vs starter       (~50k steps)  — minimal opponent
    3. vs heuristic v2  (~100k steps) — 我々の strongest baseline
    (4. vs self-history は将来追加)

Usage:
    python -m tools.train_ppo \
        --opponent heuristic \
        --total-steps 100000 \
        --output agents/proxy/ppo_v1.zip
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Heuristic v2 agent を opponent として使うために import パスを通す
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _make_opponent(kind: str):
    """opponent kind → callable agent function."""
    if kind == "random":

        def random_agent(obs, cfg):
            return []

        return random_agent
    if kind == "starter":
        # kaggle_environments built-in starter (string指定)
        from kaggle_environments import make as _km

        env = _km("orbit_wars", debug=False)
        # extract starter
        starter_fn = env.run_specs.get("agents", {}).get("starter")
        if starter_fn is None:
            raise RuntimeError("starter agent not found in kaggle_environments")
        return lambda obs, cfg: starter_fn(obs)
    if kind == "heuristic":
        # src/orbit_wars/agent.py の `agent` を import
        from orbit_wars.agent import agent as heuristic_agent

        return heuristic_agent
    if kind == "il_v2_active":
        from orbit_wars.nn_agent import make_nn_agent

        return make_nn_agent(
            _PROJECT_ROOT / "agents" / "proxy" / "il_v2.pt",
            device="cpu",
            suppress_no_op=True,
        )
    raise ValueError(f"unknown opponent kind: {kind}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--opponent", default="random", choices=["random", "starter", "heuristic", "il_v2_active"]
    )
    ap.add_argument("--total-steps", type=int, default=50000)
    ap.add_argument("--output", required=True)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--n-envs", type=int, default=4)
    ap.add_argument(
        "--shaped-reward", type=float, default=1.0, help="step-wise ship-share delta の重み"
    )
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--init-from", default=None, help="resume from this PPO checkpoint")
    args = ap.parse_args()

    print(f"opponent: {args.opponent}")
    opponent_fn = _make_opponent(args.opponent)

    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv

    from orbit_wars.gym_env import OrbitWarsEnv

    def make_env(rank):
        def _f():
            return OrbitWarsEnv(
                opponent_fn=opponent_fn,
                seed=args.seed + rank,
                shaped_reward_weight=args.shaped_reward,
            )

        return _f

    vec = DummyVecEnv([make_env(i) for i in range(args.n_envs)])

    if args.init_from:
        print(f"resuming from {args.init_from}")
        model = PPO.load(args.init_from, env=vec, device=args.device)
    else:
        print("training PPO from scratch (MLP policy)")
        model = PPO(
            "MlpPolicy",
            vec,
            verbose=1,
            device=args.device,
            n_steps=128,
            batch_size=64,
            n_epochs=4,
            learning_rate=3e-4,
            gamma=0.99,
            gae_lambda=0.95,
            clip_range=0.2,
            ent_coef=0.01,
            policy_kwargs=dict(net_arch=[256, 256]),
            seed=args.seed,
        )

    print(f"training for {args.total_steps} steps")
    model.learn(total_timesteps=args.total_steps, progress_bar=True)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    model.save(out)
    print(f"saved {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
