"""IL pretrain runner (Phase 0.4)。BC dataset で SimpleMLPPolicy を学習。

Loss: per-home cross-entropy。my_planet (= 自陣営の home として valid) でない slot は
mask out して loss から除外する (meta.parquet の n_my_planets を使う)。

Output: weights .pt を agents/proxy/ に save、tournament で動かして勝率を Print。

Usage:
    python -m tools.train_il_proxy \
        --bc-dir data/processed/bc/ \
        --output agents/proxy/il_v1.pt \
        --epochs 10 --batch-size 512
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import polars as pl
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from orbit_wars.encoders import MAX_PLANETS, PER_HOME_ACTIONS  # noqa: E402
from orbit_wars.nn_agent import SimpleMLPPolicy  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bc-dir", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--batch-size", type=int, default=512)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--val-frac", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument(
        "--class-balance",
        choices=["none", "inverse-freq", "fire-weighted"],
        default="none",
        help="no-op majority bias 対策。"
        "inverse-freq=各 class の逆頻度で weight、"
        "fire-weighted=fire class すべてに 1 つの上昇 weight",
    )
    ap.add_argument(
        "--fire-weight",
        type=float,
        default=10.0,
        help="--class-balance fire-weighted の fire class weight",
    )
    args = ap.parse_args()

    bc_dir = Path(args.bc_dir)
    states_path = bc_dir / "states.npy"
    labels_path = bc_dir / "labels.npy"
    meta_path = bc_dir / "meta.parquet"
    for p in (states_path, labels_path, meta_path):
        if not p.exists():
            print(f"missing: {p}")
            return 1

    print(f"loading {states_path}")
    states = np.load(states_path)
    labels = np.load(labels_path)
    meta = pl.read_parquet(meta_path)
    print(f"  states: {states.shape}")
    print(f"  labels: {labels.shape}")
    print(f"  meta:   {len(meta)} rows")

    n_my_planets = meta["n_my_planets"].to_numpy().astype(np.int32)

    # mask: shape (N, MAX_PLANETS), True for valid (= < n_my_planets) home
    arange = np.arange(MAX_PLANETS, dtype=np.int32)
    mask = arange[None, :] < n_my_planets[:, None]
    mask = mask.astype(np.float32)

    # train/val split (random)
    rng = np.random.default_rng(args.seed)
    n = len(states)
    perm = rng.permutation(n)
    n_val = max(1, int(n * args.val_frac))
    val_idx = perm[:n_val]
    tr_idx = perm[n_val:]
    print(f"  train: {len(tr_idx)}, val: {len(val_idx)}")

    device = torch.device(args.device)
    model = SimpleMLPPolicy().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    # class weight (no-op majority bias 対策)
    class_weight: torch.Tensor | None = None
    if args.class_balance == "inverse-freq":
        # train labels から class freq を集計
        valid_mask = mask[tr_idx].astype(bool).flatten()
        valid_labels = labels[tr_idx].flatten()[valid_mask]
        counts = np.bincount(valid_labels, minlength=PER_HOME_ACTIONS).astype(np.float64)
        # inverse + sqrt smoothing で極端な weight を避ける
        weights = 1.0 / np.sqrt(counts + 1.0)
        weights = weights / weights.mean()
        class_weight = torch.tensor(weights, dtype=torch.float32, device=device)
        print(
            f"  class weights (inverse-freq): no-op={weights[0]:.3f}, "
            f"fire mean={weights[1:].mean():.3f}, fire max={weights[1:].max():.3f}"
        )
    elif args.class_balance == "fire-weighted":
        weights = np.ones(PER_HOME_ACTIONS, dtype=np.float32)
        weights[1:] = args.fire_weight
        class_weight = torch.tensor(weights, dtype=torch.float32, device=device)
        print(f"  class weights (fire-weighted): no-op=1.0, fire={args.fire_weight}")

    # tensors as views
    s_t = torch.from_numpy(states)
    l_t = torch.from_numpy(labels.astype(np.int64))
    m_t = torch.from_numpy(mask)

    def loader(idx, batch_size, shuffle):
        ds = TensorDataset(s_t[idx], l_t[idx], m_t[idx])
        return DataLoader(ds, batch_size=batch_size, shuffle=shuffle, num_workers=0)

    tr_loader = loader(tr_idx, args.batch_size, shuffle=True)
    val_loader = loader(val_idx, args.batch_size, shuffle=False)

    print(f"training on {device}, {args.epochs} epochs")
    for ep in range(1, args.epochs + 1):
        model.train()
        tr_loss_sum = 0.0
        tr_correct = 0
        tr_seen = 0
        for s, lb, msk in tr_loader:
            s = s.to(device, non_blocking=True)
            lb = lb.to(device, non_blocking=True)
            msk = msk.to(device, non_blocking=True)
            logits = model(s)  # (B, MAX_PLANETS, PER_HOME_ACTIONS)
            B = s.size(0)
            loss_flat = F.cross_entropy(
                logits.view(-1, PER_HOME_ACTIONS),
                lb.view(-1),
                weight=class_weight,
                reduction="none",
            ).view(B, MAX_PLANETS)
            denom = msk.sum().clamp(min=1.0)
            loss = (loss_flat * msk).sum() / denom

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

            tr_loss_sum += loss.item() * denom.item()
            preds = logits.argmax(dim=-1)
            tr_correct += ((preds == lb).float() * msk).sum().item()
            tr_seen += denom.item()

        # validation
        model.eval()
        val_loss_sum = 0.0
        val_correct = 0
        val_seen = 0
        with torch.no_grad():
            for s, lb, msk in val_loader:
                s = s.to(device, non_blocking=True)
                lb = lb.to(device, non_blocking=True)
                msk = msk.to(device, non_blocking=True)
                logits = model(s)
                B = s.size(0)
                loss_flat = F.cross_entropy(
                    logits.view(-1, PER_HOME_ACTIONS),
                    lb.view(-1),
                    reduction="none",
                ).view(B, MAX_PLANETS)
                denom = msk.sum().clamp(min=1.0)
                val_loss_sum += (loss_flat * msk).sum().item()
                preds = logits.argmax(dim=-1)
                val_correct += ((preds == lb).float() * msk).sum().item()
                val_seen += denom.item()

        print(
            f"  epoch {ep:2d}: "
            f"train loss={tr_loss_sum/max(tr_seen,1):.4f} acc={tr_correct/max(tr_seen,1):.3f} | "
            f"val loss={val_loss_sum/max(val_seen,1):.4f} acc={val_correct/max(val_seen,1):.3f}"
        )

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), out)
    print(f"saved {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
