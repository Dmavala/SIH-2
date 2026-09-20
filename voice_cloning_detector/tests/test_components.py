"""
Unit Test Suite for Voice Cloning & Deepfake Speech Detection System.
"""

import os
import unittest
import numpy as np
import torch

from voice_cloning_detector.config import (
    SAMPLE_RATE, TARGET_SAMPLES, TEMPORAL_FEATURE_DIM
)
from voice_cloning_detector.feature_extraction import (
    compute_stft,
    compute_phase_spectrogram,
    extract_silence_patterns,
    extract_breathing_patterns,
    extract_pitch_jitter_shimmer,
    extract_spectral_statistics,
    extract_subband_energy_variance,
    extract_all_temporal_features
)
from voice_cloning_detector.models.branch2_phase import Branch2PhaseResNet
from voice_cloning_detector.models.branch3_temporal import Branch3Temporal
from voice_cloning_detector.dataset import (
    VoiceCloningDataset,
    split_by_speaker,
    apply_additive_noise,
    apply_codec_simulation
)
from voice_cloning_detector.train import compute_eer


class TestVoiceCloningDetector(unittest.TestCase):
    
    def setUp(self):
        self.sr = SAMPLE_RATE
        self.duration = 4.0
        # Generate 4-second synthetic test signal
        t = np.linspace(0, self.duration, int(self.sr * self.duration))
        self.audio = (0.5 * np.sin(2 * np.pi * 220 * t) + 0.2 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        
    def test_stft_computation(self):
        stft = compute_stft(self.audio, n_fft=512, hop_length=256)
        self.assertEqual(stft.shape[0], 257)
        self.assertGreater(stft.shape[1], 240)
        
    def test_phase_spectrogram(self):
        ps = compute_phase_spectrogram(self.audio, sr=self.sr, target_frames=251)
        self.assertEqual(ps.shape, (2, 257, 251))
        # Ensure finite values without NaN/Inf
        self.assertFalse(np.isnan(ps).any())
        self.assertFalse(np.isinf(ps).any())
        
    def test_silence_patterns(self):
        silence = extract_silence_patterns(self.audio, sr=self.sr)
        self.assertEqual(len(silence), 4)
        self.assertFalse(np.isnan(silence).any())
        
    def test_breathing_patterns(self):
        breath = extract_breathing_patterns(self.audio, sr=self.sr)
        self.assertEqual(len(breath), 3)
        self.assertFalse(np.isnan(breath).any())
        
    def test_pitch_jitter_shimmer(self):
        pitch_feat = extract_pitch_jitter_shimmer(self.audio, sr=self.sr)
        self.assertEqual(len(pitch_feat), 4)
        # 220 Hz sine tone fundamental frequency should be close to 220
        f0_detected = pitch_feat[0]
        self.assertAlmostEqual(f0_detected, 220.0, delta=10.0)
        
    def test_spectral_statistics(self):
        spec_stat = extract_spectral_statistics(self.audio, sr=self.sr)
        self.assertEqual(len(spec_stat), 4)
        self.assertFalse(np.isnan(spec_stat).any())
        
    def test_subband_variance(self):
        subbands = extract_subband_energy_variance(self.audio, sr=self.sr, num_bands=8)
        self.assertEqual(len(subbands), 8)
        self.assertFalse(np.isnan(subbands).any())
        
    def test_temporal_features_dimension(self):
        all_feat = extract_all_temporal_features(self.audio, sr=self.sr)
        self.assertEqual(len(all_feat), TEMPORAL_FEATURE_DIM)
        self.assertFalse(np.isnan(all_feat).any())
        
    def test_branch2_resnet_forward(self):
        model = Branch2PhaseResNet(in_channels=2, fc_hidden=128, pretrained=False)
        dummy_input = torch.randn(2, 2, 257, 251)
        out = model(dummy_input)
        self.assertEqual(out.shape, (2, 1))
        self.assertTrue((out >= 0.0).all() and (out <= 1.0).all())
        
    def test_branch3_temporal_forward(self):
        model = Branch3Temporal(input_dim=TEMPORAL_FEATURE_DIM, fc_hidden=128)
        dummy_input = torch.randn(4, TEMPORAL_FEATURE_DIM)
        out = model(dummy_input)
        self.assertEqual(out.shape, (4, 1))
        self.assertTrue((out >= 0.0).all() and (out <= 1.0).all())
        
    def test_augmentations(self):
        noisy = apply_additive_noise(self.audio)
        self.assertEqual(len(noisy), len(self.audio))
        self.assertFalse(np.isnan(noisy).any())
        
        codec = apply_codec_simulation(self.audio)
        self.assertEqual(len(codec), len(self.audio))
        self.assertFalse(np.isnan(codec).any())
        
    def test_speaker_split(self):
        records = [
            {"path": f"path_{i}.wav", "label": i % 2, "speaker": f"spk_{i % 5}"}
            for i in range(25)
        ]
        train_r, val_r, test_r = split_by_speaker(records, train_ratio=0.6, val_ratio=0.2)
        train_spks = set(r["speaker"] for r in train_r)
        val_spks = set(r["speaker"] for r in val_r)
        test_spks = set(r["speaker"] for r in test_r)
        # Assert disjoint sets
        self.assertTrue(train_spks.isdisjoint(val_spks))
        self.assertTrue(train_spks.isdisjoint(test_spks))
        self.assertTrue(val_spks.isdisjoint(test_spks))
        
    def test_eer_computation(self):
        y_true = np.array([0, 0, 0, 0, 1, 1, 1, 1])
        # Perfect scores
        y_scores = np.array([0.05, 0.1, 0.15, 0.2, 0.8, 0.85, 0.9, 0.95])
        eer, thresh = compute_eer(y_true, y_scores)
        self.assertEqual(eer, 0.0)


if __name__ == "__main__":
    unittest.main()
