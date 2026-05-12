"""Minimal stub for sb3 pickle resolution.

This module exists so cloudpickle can locate ``GridFeatureExtractor`` when
loading the trained policy from the sb3 zip. Only the class definition that
the pickled policy metadata references needs to be present -- everything
related to the training loop is intentionally absent.
"""

from __future__ import annotations

import torch
import torch.nn as nn
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor

from orbit_wars.grid_encoder import GLOBAL_FEAT_DIM, GRID_SIZE, N_CHANNELS
from orbit_wars.grid_model import GridSEResNet


class GridFeatureExtractor(BaseFeaturesExtractor):
    """Spatial features (GridSEResNet backbone) + globals -> fixed-size feature.

    This must mirror the version in ``tools/train_ppo.py`` because cloudpickle
    looks up the class by qualified name when reconstructing the policy.
    """

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
        x = self.backbone.blocks(x)
        mask = observations["action_mask"]
        mask_2d = mask.view(-1, GRID_SIZE, GRID_SIZE).unsqueeze(1)
        masked = x * mask_2d
        spatial_pool = masked.sum(dim=(2, 3)) / (mask_2d.sum(dim=(2, 3)) + 1e-6)
        feat = torch.cat([spatial_pool, globals_], dim=1)
        return self.proj(feat)
