"""
Branch 1: Self-Supervised Feature Extractor (Primary Detector).

Uses pretrained wav2vec 2.0 base (facebook/wav2vec2-base) as a FROZEN feature extractor.
A weighted average of hidden states from the last 4 transformer layers is computed using
learnable layer weights, temporally pooled, and fed to a lightweight classification head:
    Linear(768, 256) -> ReLU -> Dropout(0.3) -> Linear(256, 1) -> Sigmoid
"""

import logging
import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


class Branch1SSL(nn.Module):
    """
    Frozen Wav2Vec2 Feature Extractor with Learnable Multi-Layer Pooling and Binary Classifier Head.
    """
    def __init__(
        self,
        model_name: str = "facebook/wav2vec2-base",
        hidden_dim: int = 768,
        num_last_layers: int = 4,
        classifier_hidden: int = 256,
        dropout: float = 0.3
    ):
        super().__init__()
        self.model_name = model_name
        self.num_last_layers = num_last_layers
        self.hidden_dim = hidden_dim
        
        # Load Wav2Vec2 backbone
        try:
            from transformers import Wav2Vec2Model, Wav2Vec2Config
            logger.info(f"Loading pretrained Wav2Vec 2.0 from {model_name}...")
            self.wav2vec2 = Wav2Vec2Model.from_pretrained(
                model_name,
                output_hidden_states=True,
                attn_implementation="eager"
            )
        except Exception as e:
            logger.warning(f"Could not load pretrained weights ({e}). Initializing Wav2Vec2 with base config.")
            from transformers import Wav2Vec2Config, Wav2Vec2Model
            config = Wav2Vec2Config(
                hidden_size=hidden_dim,
                num_hidden_layers=12,
                num_attention_heads=12,
                intermediate_size=3072,
                output_hidden_states=True
            )
            self.wav2vec2 = Wav2Vec2Model(config)
            
        # Freeze ALL backbone parameters - strictly required
        for param in self.wav2vec2.parameters():
            param.requires_grad = False
            
        # Learnable softmax combination weights for the last 4 transformer layers
        self.layer_weights = nn.Parameter(torch.ones(num_last_layers, dtype=torch.float32))
        
        # Lightweight classifier head
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim, classifier_hidden),
            nn.LayerNorm(classifier_hidden),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(classifier_hidden, 1),
            nn.Sigmoid()
        )
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Raw audio waveform tensor of shape (batch_size, num_samples), e.g. (B, 64000).
            
        Returns:
            Probability tensor of shape (batch_size, 1) indicating P(fake).
        """
        # Ensure 2D (B, T)
        if x.ndim == 1:
            x = x.unsqueeze(0)
            
        # Frozen backbone extraction (no gradient computation for wav2vec2)
        with torch.no_grad():
            outputs = self.wav2vec2(x)
            # outputs.hidden_states is a tuple of (initial_embed, layer_1, ..., layer_12)
            all_hidden = outputs.hidden_states
            # Take the last num_last_layers hidden states
            selected_layers = all_hidden[-self.num_last_layers:]
            # Stack to shape (num_layers, B, T, hidden_dim)
            stacked = torch.stack(selected_layers, dim=0)
            
        # Learnable weighted combination
        norm_weights = F.softmax(self.layer_weights, dim=0)  # (4,)
        # Reshape to (4, 1, 1, 1) for broadcasting
        weighted_features = (stacked * norm_weights.view(self.num_last_layers, 1, 1, 1)).sum(dim=0)
        
        # Temporal Average Pooling across sequence length: (B, hidden_dim)
        pooled = weighted_features.mean(dim=1)
        
        # Pass through classifier head
        score = self.classifier(pooled)
        return score
