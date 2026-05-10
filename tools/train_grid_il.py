"""IL training for SE-ResNet grid policy (Phase η v2).

Trains GridSEResNet on bovard top-tier behavior cloning data.

Loss:
    Per-cell cross-entropy on action labels, ignoring cells with label=-1
    (= cells without my_planet).

Augmentation:
    Random one of 8 symmetries (4 rotations × 2 reflections) per sample,
    with angle_bin adjustment in labels.

Usage:
    python -m tools.train_grid_il \\
        --bc-dir data/processed/grid_bc/ \\
        --output agents/proxy/grid_il_v1.pt \\
        --epochs 20 --batch-size 64 --lr 1e-3
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from orbit_wars.grid_encoder import augment_grid  # noqa: E402
from orbit_wars.grid_model import GridSEResNet, count_params  # noqa: E402


class GridBCDataset(Dataset):
    def __init__(self, bc_dir: Path, train: bool = True, val_frac: float = 0.1, seed: int = 42):
        self.spatial = np.load(bc_dir / "spatial.npy", mmap_mode="r")
        self.globals_ = np.load(bc_dir / "globals.npy", mmap_mode="r")
        self.labels = np.load(bc_dir / "labels.npy", mmap_mode="r")
        n = len(self.spatial)
        rng = np.random.default_rng(seed)
        perm = rng.permutation(n)
        n_val = max(1, int(n * val_frac))
        self.indices = perm[n_val:] if train else perm[:n_val]
        self.train = train

    def __len__(self) -> int:
        return len(self.indices)

    def __getitem__(self, i: int):
        idx = int(self.indices[i])
        spatial = self.spatial[idx].astype(np.float32)  # (14, 64, 64)
        globals_ = self.globals_[idx].astype(np.float32)  # (9,)
        labels = self.labels[idx].astype(np.int64)  # (64, 64), -128 = ignore
        if self.train:
            # random one of 8 symmetries
            mode = np.random.randint(0, 8)
            spatial, labels = augment_grid(spatial, labels, mode)
            labels = labels.astype(np.int64)
        return (
            torch.from_numpy(spatial.copy()),
            torch.from_numpy(globals_),
            torch.from_numpy(labels.copy()),
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bc-dir", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--val-frac", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--num-workers", type=int, default=2)
    ap.add_argument(
        "--fire-weight",
        type=float,
        default=1.0,
        help="multiplier for fire-class loss (vs no-op). >1 to counter no-op bias.",
    )
    args = ap.parse_args()

    bc_dir = Path(args.bc_dir)
    train_ds = GridBCDataset(bc_dir, train=True, val_frac=args.val_frac, seed=args.seed)
    val_ds = GridBCDataset(bc_dir, train=False, val_frac=args.val_frac, seed=args.seed)
    print(f"train: {len(train_ds)}, val: {len(val_ds)}")

    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        pin_memory=True,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        pin_memory=True,
    )

    device = torch.device(args.device)
    model = GridSEResNet().to(device)
    print(f"params: {count_params(model):,}")
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    # Class weight: counter no-op majority bias.
    # All fire classes (1..80) get `fire_weight`, no-op (0) keeps weight 1.0.
    PER_CELL_ACTIONS = 81
    class_weight = torch.ones(PER_CELL_ACTIONS, dtype=torch.float32, device=device)
    class_weight[1:] = args.fire_weight
    if args.fire_weight != 1.0:
        print(f"  class weight: no_op=1.0, fire={args.fire_weight}")

    # `-128` was used as the int8 sentinel for "ignore" cells (= no my_planet).
    # Convert to int64's CrossEntropy ignore_index of -100.
    IGNORE = -100

    def _to_loss_labels(labels: torch.Tensor) -> torch.Tensor:
        """Map -128 → -100 (cross_entropy default ignore_index)."""
        out = labels.clone()
        out[out < 0] = IGNORE
        return out

    print(f"training {args.epochs} epochs on {device}")
    best_val_acc = 0.0
    for ep in range(1, args.epochs + 1):
        model.train()
        tr_loss = 0.0
        tr_correct = 0
        tr_seen = 0
        for spatial, globals_, labels in train_loader:
            spatial = spatial.to(device, non_blocking=True)
            globals_ = globals_.to(device, non_blocking=True)
            labels = _to_loss_labels(labels.to(device, non_blocking=True))

            logits, _ = model(spatial, globals_)  # (B, H, W, K)
            B, H, W, K = logits.shape
            loss = F.cross_entropy(
                logits.reshape(-1, K),
                labels.reshape(-1),
                weight=class_weight,
                ignore_index=IGNORE,
            )
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

            with torch.no_grad():
                preds = logits.argmax(dim=-1)
                mask = labels != IGNORE
                tr_correct += (preds == labels)[mask].sum().item()
                tr_seen += int(mask.sum().item())
            tr_loss += loss.item() * spatial.size(0)

        # val
        model.eval()
        val_correct = 0
        val_seen = 0
        val_loss = 0.0
        with torch.no_grad():
            for spatial, globals_, labels in val_loader:
                spatial = spatial.to(device, non_blocking=True)
                globals_ = globals_.to(device, non_blocking=True)
                labels = _to_loss_labels(labels.to(device, non_blocking=True))
                logits, _ = model(spatial, globals_)
                K = logits.size(-1)
                loss = F.cross_entropy(
                    logits.reshape(-1, K), labels.reshape(-1), ignore_index=IGNORE
                )
                preds = logits.argmax(dim=-1)
                mask = labels != IGNORE
                val_correct += (preds == labels)[mask].sum().item()
                val_seen += int(mask.sum().item())
                val_loss += loss.item() * spatial.size(0)

        tr_acc = tr_correct / max(tr_seen, 1)
        val_acc = val_correct / max(val_seen, 1)
        print(
            f"  epoch {ep:2d}: train loss={tr_loss/len(train_ds):.4f} acc={tr_acc:.3f} | "
            f"val loss={val_loss/len(val_ds):.4f} acc={val_acc:.3f}"
        )
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            out = Path(args.output)
            out.parent.mkdir(parents=True, exist_ok=True)
            torch.save({"state_dict": model.state_dict(), "val_acc": val_acc}, out)
            print(f"    saved best to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
