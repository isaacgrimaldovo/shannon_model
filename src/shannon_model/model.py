"""Modelo baseline placeholder para shannon_model."""

from __future__ import annotations

import torch
import torch.nn as nn


class ShannonBaseline(nn.Module):
    """Baseline MLP. Sustituir por la arquitectura real cuando esté definida."""

    def __init__(
        self,
        input_size: int = 64,
        hidden_size: int = 256,
        num_classes: int = 2,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)
