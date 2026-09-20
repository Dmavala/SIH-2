"""
Branch 2: Phase-Aware Spectrogram Classifier (ResNet-18).

Takes dual-channel STFT input:
  Channel 0: Log-magnitude STFT
  Channel 1: Instantaneous frequency deviation (time-derivative of unwrapped phase)
Uses a ResNet-18 backbone with a modified 2-channel first convolutional layer and a
binary classification head:
  Linear(512, 128) -> ReLU -> Dropout(0.3) -> Linear(128, 1) -> Sigmoid
"""

import logging
import ssl
import torch
import torch.nn as nn
from torchvision.models import resnet18, ResNet18_Weights

logger = logging.getLogger(__name__)

# Handle macOS certificate verify issue for PyTorch hub
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except Exception:
    pass


class Branch2PhaseResNet(nn.Module):
    """
    Phase-Aware ResNet-18 Classifier for Dual-Channel Phase and Magnitude Spectrograms.
    """
    def __init__(
        self,
        in_channels: int = 2,
        fc_hidden: int = 128,
        dropout: float = 0.3,
        pretrained: bool = True
    ):
        super().__init__()
        
        # Load ResNet-18 with ImageNet weights if available
        try:
            if pretrained:
                base_model = resnet18(weights=ResNet18_Weights.DEFAULT)
            else:
                base_model = resnet18(weights=None)
        except Exception as e:
            logger.warning(f"Could not download ImageNet weights ({e}), initializing unweighted ResNet-18.")
            base_model = resnet18(weights=None)
            
        # Adapt conv1 for 2 input channels
        orig_conv1 = base_model.conv1
        new_conv1 = nn.Conv2d(
            in_channels=in_channels,
            out_channels=orig_conv1.out_channels,
            kernel_size=orig_conv1.kernel_size,
            stride=orig_conv1.stride,
            padding=orig_conv1.padding,
            bias=False
        )
        
        # Transfer pretrained weights from first 2 channels
        with torch.no_grad():
            if orig_conv1.weight is not None:
                new_conv1.weight.copy_(orig_conv1.weight[:, :in_channels, :, :])
                
        base_model.conv1 = new_conv1
        
        # Replace the original classification FC layer with a binary classification head
        in_features = base_model.fc.in_features  # 512
        base_model.fc = nn.Sequential(
            nn.Linear(in_features, fc_hidden),
            nn.LayerNorm(fc_hidden),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(fc_hidden, 1),
            nn.Sigmoid()
        )
        
        self.model = base_model
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Spectrogram tensor of shape (batch_size, 2, H, W), e.g. (B, 2, 257, 251).
            
        Returns:
            Probability tensor of shape (batch_size, 1) indicating P(fake).
        """
        if x.ndim == 3:
            x = x.unsqueeze(0)  # (1, 2, H, W)
        return self.model(x)
