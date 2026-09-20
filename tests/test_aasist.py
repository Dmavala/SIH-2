"""
Unit & Latency Tests for AASIST (Spectro-Temporal Graph Attention) & RawNet2.
"""

import unittest
import torch
import numpy as np
from backend.models.aasist import AASIST, SincConv
from backend.models.rawnet import RawNet2
from backend.models.detector import DeepfakeDetector


class TestAASISTAndRawNet(unittest.TestCase):

    def setUp(self):
        self.device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
        self.sample_rate = 16000
        # 2 seconds raw waveform
        self.raw_audio = torch.randn(1, 32000, device=self.device)

    def test_sinc_conv_layer(self):
        sinc = SincConv(out_channels=70, kernel_size=128, sample_rate=self.sample_rate).to(self.device)
        out = sinc(self.raw_audio.unsqueeze(1))
        # Expected shape: (1, 70, 16000) due to stride=2
        self.assertEqual(out.shape[1], 70)
        self.assertFalse(torch.isnan(out).any())

    def test_aasist_forward(self):
        model = AASIST(sample_rate=self.sample_rate).to(self.device).eval()
        with torch.no_grad():
            logits = model(self.raw_audio)
            self.assertEqual(logits.shape, (1, 2))
            prob = model.predict_spoof_prob(self.raw_audio)
            self.assertTrue(0.0 <= prob <= 1.0)

    def test_rawnet2_forward(self):
        model = RawNet2(sample_rate=self.sample_rate).to(self.device).eval()
        with torch.no_grad():
            logits = model(self.raw_audio)
            self.assertEqual(logits.shape, (1, 2))
            prob = model.predict_spoof_prob(self.raw_audio)
            self.assertTrue(0.0 <= prob <= 1.0)

    def test_detector_integration_with_aasist(self):
        detector = DeepfakeDetector(model_type="aasist", use_gpu=True)
        self.assertEqual(detector.model_type, "aasist")
        
        # Test on numpy waveform
        audio_np = np.random.normal(0, 0.1, 32000).astype(np.float32)
        res = detector.analyze_audio(audio_np, sample_rate=16000)
        
        self.assertIn("AASIST", res["model_architecture"])
        self.assertIn("risk_score", res)
        self.assertIn("forensics", res)
        # Verify latency is strictly < 50ms
        self.assertLess(res["latency_ms"], 50.0)
        print(f"\n[AASIST INTEGRATION] Latency: {res['latency_ms']} ms | Model: {res['model_architecture']} | Device: {res['device']}")

    def test_detector_model_switching(self):
        detector = DeepfakeDetector(model_type="aasist")
        detector.set_model_type("rawnet")
        self.assertEqual(detector.model_type, "rawnet")
        
        audio_np = np.random.normal(0, 0.1, 32000).astype(np.float32)
        res = detector.analyze_audio(audio_np, sample_rate=16000)
        self.assertIn("RawNet2", res["model_architecture"])


if __name__ == "__main__":
    unittest.main()
