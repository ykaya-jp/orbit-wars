"""Train a numpy MLP shot validator on the bovard-derived dataset.

Replicates konbu17 architecture:
    24 → 64 (ReLU) → 32 (ReLU) → 1 (sigmoid)

Loss: BCEWithLogits with pos_weight = neg/pos.

Output: weights.npz with keys w0, b0, w2, b2, w4, b4 (matches konbu17 _NumpyValidator).

Usage:
    python -m tools.train_validator \
        --dataset data/processed/validator/ \
        --output agents/proxy/validator_v2.npz \
        --epochs 40 --batch-size 256 --lr 1e-3
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class ValidatorMLP(nn.Module):
    def __init__(self, in_dim: int = 24, h1: int = 64, h2: int = 32):
        super().__init__()
        self.fc0 = nn.Linear(in_dim, h1)
        self.fc2 = nn.Linear(h1, h2)
        self.fc4 = nn.Linear(h2, 1)

    def forward(self, x):
        h = F.relu(self.fc0(x))
        h = F.relu(self.fc2(h))
        return self.fc4(h).squeeze(-1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--batch-size", type=int, default=256)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--val-frac", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = ap.parse_args()

    ds = Path(args.dataset)
    feats = np.load(ds / "feats.npy")
    labels = np.load(ds / "labels.npy").astype(np.float32)
    print(f"loaded {feats.shape} feats, {labels.shape} labels")
    pos_rate = labels.mean()
    print(f"  positive rate: {pos_rate:.3f}")

    rng = np.random.default_rng(args.seed)
    perm = rng.permutation(len(feats))
    n_val = max(1, int(len(feats) * args.val_frac))
    val_idx = perm[:n_val]
    tr_idx = perm[n_val:]

    device = torch.device(args.device)
    model = ValidatorMLP().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    pos = labels[tr_idx].sum()
    neg = (1.0 - labels[tr_idx]).sum()
    pos_weight = torch.tensor(neg / max(pos, 1.0), dtype=torch.float32, device=device)
    print(f"  pos_weight: {pos_weight.item():.3f}")

    Xtr = torch.from_numpy(feats[tr_idx]).to(device)
    Ytr = torch.from_numpy(labels[tr_idx]).to(device)
    Xva = torch.from_numpy(feats[val_idx]).to(device)
    Yva = torch.from_numpy(labels[val_idx]).to(device)

    bs = args.batch_size
    n = len(tr_idx)
    print(f"training {args.epochs} epochs, {n} samples, batch {bs}")
    for ep in range(1, args.epochs + 1):
        model.train()
        order = torch.randperm(n, device=device)
        loss_sum = 0.0
        correct = 0
        for s in range(0, n, bs):
            idx = order[s : s + bs]
            x = Xtr[idx]
            y = Ytr[idx]
            logits = model(x)
            loss = F.binary_cross_entropy_with_logits(logits, y, pos_weight=pos_weight)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            loss_sum += loss.item() * len(idx)
            preds = (torch.sigmoid(logits) > 0.5).float()
            correct += (preds == y).sum().item()
        # validation
        model.eval()
        with torch.no_grad():
            v_logits = model(Xva)
            v_pred = (torch.sigmoid(v_logits) > 0.5).float()
            v_acc = (v_pred == Yva).float().mean().item()
            v_acc_t04 = ((torch.sigmoid(v_logits) > 0.4).float() == Yva).float().mean().item()
            v_pos = ((torch.sigmoid(v_logits) > 0.5).float()).mean().item()
        print(
            f"  epoch {ep:2d}: train loss={loss_sum/n:.4f} acc={correct/n:.3f} | "
            f"val acc(0.5)={v_acc:.3f} acc(0.4)={v_acc_t04:.3f} pred_pos_rate={v_pos:.3f}"
        )

    # Export to konbu17 format
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    sd = model.state_dict()
    np.savez(
        out,
        w0=sd["fc0.weight"].cpu().numpy().astype(np.float32),
        b0=sd["fc0.bias"].cpu().numpy().astype(np.float32),
        w2=sd["fc2.weight"].cpu().numpy().astype(np.float32),
        b2=sd["fc2.bias"].cpu().numpy().astype(np.float32),
        w4=sd["fc4.weight"].cpu().numpy().astype(np.float32),
        b4=sd["fc4.bias"].cpu().numpy().astype(np.float32),
    )
    print(f"saved {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
