"""SE-ResNet policy network for orbit-wars (Phase η v2).

Input:
    spatial (B, 14, 64, 64) — multi-channel grid (planets, fleets, sun, ...)
    globals_ (B, 9)        — step, angular_velocity, totals, phase one-hot

Output:
    logits (B, 64, 64, 81) — per-cell action distribution
    value (B,)             — state value estimate (for PPO; ignored in BC)

Architecture (lightweight):
    spatial → conv 3x3 → 4 × SE-ResNet block (32 channels) → conv 1x1 (81 ch)
    globals_ → MLP(64) → broadcast + spatial concat
    Final logits: spatial output + globals_ MLP output projected per-cell
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

GRID_SIZE = 64
N_CHANNELS = 14
GLOBAL_FEAT_DIM = 9
PER_CELL_ACTIONS = 81


class SEBlock(nn.Module):
    """Squeeze-and-Excitation channel-attention block."""

    def __init__(self, channels: int, reduction: int = 4):
        super().__init__()
        red = max(channels // reduction, 4)
        self.fc = nn.Sequential(
            nn.Linear(channels, red),
            nn.ReLU(inplace=True),
            nn.Linear(red, channels),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, C, H, W)
        gap = x.mean(dim=(2, 3))
        scale = self.fc(gap).unsqueeze(-1).unsqueeze(-1)
        return x * scale


class ResBlock(nn.Module):
    """Residual block with optional SE."""

    def __init__(self, channels: int, use_se: bool = True):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, 3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(channels)
        self.conv2 = nn.Conv2d(channels, channels, 3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(channels)
        self.se = SEBlock(channels) if use_se else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        identity = x
        x = F.relu(self.bn1(self.conv1(x)), inplace=True)
        x = self.bn2(self.conv2(x))
        x = self.se(x)
        x = F.relu(x + identity, inplace=True)
        return x


class GridSEResNet(nn.Module):
    """Compact SE-ResNet for orbit-wars 14×64×64 input."""

    def __init__(
        self,
        in_channels: int = N_CHANNELS,
        base_channels: int = 32,
        n_blocks: int = 4,
        global_feat_dim: int = GLOBAL_FEAT_DIM,
        n_actions: int = PER_CELL_ACTIONS,
    ):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Conv2d(in_channels, base_channels, 3, padding=1, bias=False),
            nn.BatchNorm2d(base_channels),
            nn.ReLU(inplace=True),
        )
        self.blocks = nn.Sequential(*[ResBlock(base_channels) for _ in range(n_blocks)])

        # Global features → broadcast spatially
        self.global_mlp = nn.Sequential(
            nn.Linear(global_feat_dim, 64),
            nn.ReLU(inplace=True),
            nn.Linear(64, base_channels),
        )

        # Policy head: per-cell logits
        self.policy_head = nn.Conv2d(base_channels, n_actions, 1)

        # Value head: GAP + MLP
        self.value_head = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(base_channels, 64),
            nn.ReLU(inplace=True),
            nn.Linear(64, 1),
        )

    def forward(
        self, spatial: torch.Tensor, globals_: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            spatial: (B, in_channels, H, W)
            globals_: (B, global_feat_dim)

        Returns:
            logits: (B, H, W, n_actions)
            value: (B,)
        """
        x = self.stem(spatial)
        # broadcast globals onto spatial dim
        g = self.global_mlp(globals_)  # (B, base_channels)
        g = g.unsqueeze(-1).unsqueeze(-1)  # (B, C, 1, 1)
        x = x + g  # element-wise add
        x = self.blocks(x)
        logits = self.policy_head(x)  # (B, n_actions, H, W)
        logits = logits.permute(0, 2, 3, 1)  # (B, H, W, n_actions)
        value = self.value_head(x).squeeze(-1)
        return logits, value


def count_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


if __name__ == "__main__":
    # smoke test
    model = GridSEResNet()
    print(f"params: {count_params(model):,}")
    spatial = torch.randn(2, N_CHANNELS, GRID_SIZE, GRID_SIZE)
    globals_ = torch.randn(2, GLOBAL_FEAT_DIM)
    logits, value = model(spatial, globals_)
    print(f"logits: {logits.shape}")
    print(f"value: {value.shape}")
