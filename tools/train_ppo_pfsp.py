"""PPO θ.4 — true PFSP (Prioritized Fictitious Self-Play) trainer.

Extends tools/train_ppo.py with:
  - Self-history pool (= 学習中の自身の checkpoint を動的追加、 最大 N=8)
  - PFSP opponent sampling weight: w_i ∝ (1.0 - win_rate_i)^2 (AlphaStar Nature 2019)
  - 5% uniform mixture to prevent collapse
  - Warm-start from θ.3 zip
  - External opponents mix (= fixed rule-base / IL agents complement self-play)

Usage:
    python -m tools.train_ppo_pfsp \\
        --total-timesteps 100000 \\
        --n-envs 8 \\
        --warm-start agents/proxy/ppo_v3_theta3.zip \\
        --external-opponents agents/proxy/grid_il_lakhindar.py \\
                             submissions/build_konbu_topk1/main.py \\
        --pool-max 8 \\
        --save-interval 2000 \\
        --output agents/proxy/ppo_v4_theta4.zip

Reference:
  - AlphaStar PFSP (Vinyals et al., Nature 2019)
  - Lux S3 1st Frog Parade (IL → PPO + self-play, 8 day RTX 3090)
  - tools/train_ppo.py (= θ.1-θ.3 trainer 基盤)
"""

from __future__ import annotations

import argparse
import random
import shutil
import sys
from pathlib import Path

import torch
from sb3_contrib import MaskablePPO
from sb3_contrib.common.maskable.policies import MaskableMultiInputActorCriticPolicy
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.vec_env import DummyVecEnv

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))
_SRC = _TOOLS.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Reuse heavy lifting from tools/train_ppo.py (= GridFeatureExtractor, env, opponents)
from orbit_wars_env import OrbitWarsEnv  # noqa: E402
from train_ppo import (  # noqa: E402
    GridFeatureExtractor,
    make_file_opponent,
    make_random_opponent,
    mask_fn,
)

# ====================================================================
# Self-history pool (= self_history) with PFSP weighting
# ====================================================================


def pfsp_weight_from_wr(win_rate: float) -> float:
    """PFSP weight: w_i ∝ (1.0 - win_rate)^2.

    Source: AlphaStar Nature 2019. Higher weight = opponent we lose against more.
    """
    return max(0.0, (1.0 - win_rate)) ** 2


class SelfHistoryPool:
    """In-memory + on-disk pool of self-history checkpoints with PFSP weighting.

    Entries are (zip_path, win_rate) ordered FIFO (= oldest first).
    When at max_size, oldest is evicted and its file is removed.
    """

    UNIFORM_MIX = 0.05  # 5% uniform mixture for diversity

    def __init__(self, pool_dir: Path, max_size: int = 8):
        self.pool_dir = Path(pool_dir)
        self.pool_dir.mkdir(parents=True, exist_ok=True)
        self.max_size = max_size
        self.entries: list[tuple[str, float]] = []

    def add(self, ckpt_path: str, initial_win_rate: float = 0.5) -> None:
        if len(self.entries) >= self.max_size:
            removed_path, _ = self.entries.pop(0)  # FIFO evict oldest
            try:
                rp = Path(removed_path)
                # Only delete if it's inside our pool_dir (= we own it)
                if rp.is_relative_to(self.pool_dir):
                    rp.unlink(missing_ok=True)
            except Exception:
                pass
        self.entries.append((ckpt_path, initial_win_rate))

    def update_win_rate(self, path: str, win_rate: float) -> None:
        for i, (p, _) in enumerate(self.entries):
            if p == path:
                self.entries[i] = (p, win_rate)
                return

    def pfsp_weights(self) -> list[float]:
        """w_i ∝ (1.0 - win_rate_i)^2, with UNIFORM_MIX uniform mixture."""
        if not self.entries:
            return []
        raw = [pfsp_weight_from_wr(wr) for _, wr in self.entries]
        total = sum(raw)
        n = len(self.entries)
        if total <= 0:
            return [1.0 / n] * n
        normed = [r / total for r in raw]
        return [(1.0 - self.UNIFORM_MIX) * w + self.UNIFORM_MIX / n for w in normed]

    def sample_path(self) -> str | None:
        if not self.entries:
            return None
        weights = self.pfsp_weights()
        idx = random.choices(range(len(self.entries)), weights=weights, k=1)[0]
        return self.entries[idx][0]


# ====================================================================
# Self-opponent loader (= reuse ppo_inference.make_ppo_agent)
# ====================================================================

_SELF_OPP_CACHE: dict[str, object] = {}
_SELF_OPP_BAD: set[str] = set()  # cache of paths that previously failed to load


def make_self_opponent(zip_path: str, device: str = "cpu"):
    """Load a PPO checkpoint zip as a kaggle_environments agent function.

    Cached per-path to avoid repeated heavy load. Failed paths are cached in
    `_SELF_OPP_BAD` so warnings emit only once.
    """
    if zip_path in _SELF_OPP_CACHE:
        return _SELF_OPP_CACHE[zip_path]
    if zip_path in _SELF_OPP_BAD:
        raise RuntimeError("self-opponent previously failed (cached skip)")
    # Reuse the inference adapter already used for submit
    sub_dir = _TOOLS.parent / "submissions" / "build_ppo_v3_theta3"
    if str(sub_dir) not in sys.path:
        sys.path.insert(0, str(sub_dir))
    from ppo_inference import make_ppo_agent  # type: ignore  # noqa: E402

    fn = make_ppo_agent(zip_path, device=device, deterministic=False)
    _SELF_OPP_CACHE[zip_path] = fn
    return fn


# ====================================================================
# PFSP checkpoint save callback
# ====================================================================


class PFSPCallback(BaseCallback):
    """Periodically save current policy to self-history pool.

    Win-rate measurement is deferred to a separate eval pass (= not done in
    this callback to keep training throughput high). Initial weight is 0.5
    (= uniform priors), which gives the new checkpoint moderate sampling
    probability until its real win rate is measured.
    """

    def __init__(
        self,
        pool: SelfHistoryPool,
        save_interval: int,
        verbose: int = 1,
    ):
        super().__init__(verbose)
        self.pool = pool
        self.save_interval = save_interval
        self.next_save_step = save_interval

    def _on_step(self) -> bool:
        if self.num_timesteps >= self.next_save_step:
            ckpt_path = self.pool.pool_dir / f"ckpt_step_{self.num_timesteps}.zip"
            self.model.save(str(ckpt_path))
            self.pool.add(str(ckpt_path), initial_win_rate=0.5)
            if self.verbose >= 1:
                names = [Path(p).name for p, _ in self.pool.entries]
                print(
                    f"[PFSP] step={self.num_timesteps} "
                    f"pool_size={len(self.pool.entries)} entries={names}"
                )
            self.next_save_step += self.save_interval
        return True


# ====================================================================
# Main
# ====================================================================


def _build_sample_opponents(
    pool: SelfHistoryPool,
    external_fns: list,
    self_play_prob: float,
    external_prob: float,
    device: str,
):
    """Closure that returns 3 opponent fns per env.reset (= per episode).

    Sampling priority: PFSP self-history (self_play_prob) > external (external_prob)
    > random (= residual). Each of 3 slots is sampled independently.
    """

    def sample_opponents() -> list:
        opps: list = []
        for _ in range(3):
            r = random.random()
            placed = False
            if r < self_play_prob and pool.entries:
                p = pool.sample_path()
                if p is not None:
                    try:
                        opps.append(make_self_opponent(p, device=device))
                        placed = True
                    except Exception as exc:
                        if p not in _SELF_OPP_BAD:
                            print(f"  [warn] failed to load self-opponent {p}: {exc}")
                            _SELF_OPP_BAD.add(p)
            if not placed and r < self_play_prob + external_prob and external_fns:
                opps.append(random.choice(external_fns))
                placed = True
            if not placed:
                opps.append(make_random_opponent())
        return opps

    return sample_opponents


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
    ap.add_argument("--output", default="agents/proxy/ppo_v4_theta4.zip")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--reward-shaping", action="store_true")
    ap.add_argument(
        "--warm-start",
        default=None,
        help="Path to PPO zip to start training from (= θ.3 zip recommended)",
    )
    ap.add_argument(
        "--external-opponents",
        nargs="*",
        default=[],
        help="Fixed rule-base/IL agents to mix with self-history pool",
    )
    ap.add_argument("--pool-max", type=int, default=8, help="Self-history pool max size")
    ap.add_argument(
        "--save-interval",
        type=int,
        default=2000,
        help="Steps between checkpoint saves to self-history pool",
    )
    ap.add_argument("--pool-dir", default="outputs/ppo_pfsp_pool")
    ap.add_argument(
        "--self-play-prob",
        type=float,
        default=0.6,
        help="Per-slot probability of sampling from self-history pool",
    )
    ap.add_argument(
        "--external-prob",
        type=float,
        default=0.3,
        help="Per-slot probability of sampling from external opponents (= conditional)",
    )
    args = ap.parse_args()

    print(f"PFSP-PPO: {args.total_timesteps} steps, {args.n_envs} envs, device={args.device}")
    print(f"  warm-start: {args.warm_start}")
    print(f"  pool: dir={args.pool_dir} max={args.pool_max} save_interval={args.save_interval}")
    print(f"  external opponents: {args.external_opponents}")
    print(f"  sample prob: self_play={args.self_play_prob} external={args.external_prob}")

    pool = SelfHistoryPool(Path(args.pool_dir), max_size=args.pool_max)

    # Bootstrap pool from warm-start (= θ.3 zip)
    if args.warm_start:
        bootstrap = Path(args.pool_dir) / "bootstrap_warmstart.zip"
        bootstrap.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(args.warm_start, bootstrap)
        pool.add(str(bootstrap), initial_win_rate=0.5)
        print(f"  pool bootstrap added: {bootstrap}")

    # Pre-load external opponents (= rule-base / IL .py files)
    external_fns: list = []
    for spec in args.external_opponents:
        external_fns.append(make_file_opponent(spec))

    sample_opponents = _build_sample_opponents(
        pool=pool,
        external_fns=external_fns,
        self_play_prob=args.self_play_prob,
        external_prob=args.external_prob,
        device="cpu",  # opponents run on CPU to free GPU for training
    )

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

    if args.warm_start:
        # ALWAYS bypass MaskablePPO.load() full deserialize (= sb3 major version mismatch
        # で SIGSEGV in C ext を try/except でも catch 不可。 weights-only load で確実。)
        # 結果: policy weights は IL pretrain 維持、 optimizer state は fresh。
        print(f"  loading warm-start weights from {args.warm_start} (weights-only mode)")
        import io
        import zipfile
        import torch as _torch

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
        with zipfile.ZipFile(args.warm_start) as zf:
            with zf.open("policy.pth") as pf:
                sd = _torch.load(
                    io.BytesIO(pf.read()), map_location=args.device, weights_only=True
                )
        missing, unexpected = model.policy.load_state_dict(sd, strict=False)
        if missing:
            print(f"  [warn] missing keys ({len(missing)}): {missing[:3]}...")
        if unexpected:
            print(f"  [warn] unexpected keys ({len(unexpected)}): {unexpected[:3]}...")
        print("  policy weights loaded successfully")
    else:
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

    callback = PFSPCallback(pool, save_interval=args.save_interval, verbose=1)
    model.learn(
        total_timesteps=args.total_timesteps,
        callback=callback,
        progress_bar=False,
    )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(str(out_path))
    print(f"saved: {out_path}")
    print(f"final pool size: {len(pool.entries)}")
    print("final pool entries: " f"{[(Path(p).name, round(wr, 3)) for p, wr in pool.entries]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
