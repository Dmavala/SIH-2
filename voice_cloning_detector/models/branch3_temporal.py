"""
Branch 3: Hand-Crafted Temporal & Biological Artifacts Classifier.

Takes 23-dimensional feature vector containing:
  - Silence pattern dynamics (4 dims)
  - Breathing detection in 100-1000Hz (3 dims)
  - Pitch Jitter and Shimmer (4 dims)
  - Long-term spectral statistics (4 dims)
  - Sub-band energy temporal variance across 8 bands (8 dims)
Architecture:
  Linear(23, 128) -> LayerNorm -> ReLU -> Dropout(0.3) -> Linear(128, 1) -> Sigmoid
"""

import torch
import torch.nn as nn


class Branch3Temporal(nn.Module):
    """
    Multilayer Perceptron Classifier for Hand-Crafted Acoustic & Biological Speech Artifacts.
    """
    def __init__(
        self,
        input_dim: int = 23,
        fc_hidden: int = 128,
        dropout: float = 0.3
    ):
        super().__init__()
        self.input_dim = input_dim
        
        self.classifier = nn.Sequential(
            nn.Linear(input_dim, fc_hidden),
            nn.LayerNorm(fc_hidden),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(fc_hidden, 1),
            nn.Sigmoid()
        )
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Temporal feature tensor of shape (batch_size, 23).
            
        Returns:
            Probability tensor of shape (batch_size, 1) indicating P(fake).
        """
        if x.ndim == 1:
            x = x.unsqueeze(0)
        return self.classifier(x)
