"""
Feature Extraction Unit & Latency Tests for SIH Audio Deepfake Detector.
"""

import unittest
import os
import time
import numpy as np
import soundfile as sf
from backend.features.lfcc import extract_lfcc, linear_filterbank
from backend.features.acoustics import extract_acoustic_forensics
from backend.features.augmentations import apply_telephony_filter
from backend.models.detector import DeepfakeDetector
from backend.pipeline.prevention import PreventionManager, ThreatAggregator
from backend.pipeline.stream_processor import StreamProcessor


class TestDeepfakeFeatures(unittest.TestCase):

    def setUp(self):
        self.sample_rate = 16000
        # 1.5 seconds synthetic test sine tone
        t = np.linspace(0, 1.5, int(self.sample_rate * 1.5), endpoint=False)
        self.sine_audio = (0.5 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)

    def test_linear_filterbank_shape(self):
        n_fft = 512
        num_filters = 60
        fbank = linear_filterbank(num_filters, n_fft, self.sample_rate)
        self.assertEqual(fbank.shape, (num_filters, n_fft // 2 + 1))
        # Ensure filterbank has nonzero weights
        self.assertTrue(np.sum(fbank) > 0)

    def test_lfcc_extraction(self):
        lfcc = extract_lfcc(self.sine_audio, sample_rate=self.sample_rate, num_filters=60, num_ceps=20)
        # 20 base ceps + 20 delta + 20 delta-delta = 60 features
        self.assertEqual(lfcc.shape[1], 60)
        self.assertTrue(lfcc.shape[0] > 10)
        self.assertFalse(np.isnan(lfcc).any())

    def test_acoustic_forensics_keys(self):
        acoustics = extract_acoustic_forensics(self.sine_audio, sample_rate=self.sample_rate)
        required_keys = [
            "pitch_mean", "pitch_std", "jitter_local", "shimmer_local",
            "phase_dispersion", "high_band_ratio", "breath_pause_ratio",
            "spectral_flatness", "ambient_noise_floor_db", "is_pristine_env"
        ]
        for key in required_keys:
            self.assertIn(key, acoustics)

    def test_telephony_filter(self):
        filtered = apply_telephony_filter(self.sine_audio, fs=self.sample_rate)
        self.assertEqual(len(filtered), len(self.sine_audio))
        self.assertFalse(np.isnan(filtered).any())


class TestDetectorAndLatency(unittest.TestCase):

    def setUp(self):
        self.detector = DeepfakeDetector()

    def test_latency_under_60ms(self):
        # Test 1-second audio frame latency on CPU
        sr = 16000
        audio_frame = np.random.normal(0, 0.1, sr).astype(np.float32)

        latencies = []
        # Warmup
        self.detector.analyze_audio(audio_frame, sample_rate=sr)

        for _ in range(25):
            res = self.detector.analyze_audio(audio_frame, sample_rate=sr)
            latencies.append(res["latency_ms"])

        avg_latency = np.mean(latencies)
        p95_latency = np.percentile(latencies, 95)
        print(f"\n[BENCHMARK] Average Frame Latency: {avg_latency:.2f} ms | P95: {p95_latency:.2f} ms")

        # Hard limit from user prompt: strictly < 150ms. Our target is < 60ms.
        self.assertLess(avg_latency, 60.0)
        self.assertLess(p95_latency, 100.0)

    def test_benchmark_audio_classification(self):
        """
        Consensus-era semantics over REAL recordings (built via
        scripts/build_real_demo_samples.py). The system runs BOTH engines and
        abstains (INCONCLUSIVE) when they disagree or the fused score sits in
        the gray zone. Safety properties asserted here:
          - Real audio is NEVER classified CRITICAL_SYNTHETIC (no false alarm).
          - Known deepfakes/scams are NEVER classified AUTHENTIC_HUMAN (no missed attack).
          - Every result carries a consensus block.
        """
        samples_dir = "backend/demo_audio/samples"
        files = [
            os.path.join(samples_dir, "real_authentic_speech.wav"),
            os.path.join(samples_dir, "real_authentic_indian_accent.wav"),
            os.path.join(samples_dir, "real_authentic_telephony.wav"),
            os.path.join(samples_dir, "real_deepfake_elevenlabs.wav"),
            os.path.join(samples_dir, "real_deepfake_hifigan.wav"),
            os.path.join(samples_dir, "real_scam_digital_arrest.wav"),
        ]

        for path in files:
            audio, sr = sf.read(path)
            res = self.detector.analyze_audio(audio, sample_rate=sr)
            is_fake = "deepfake" in path or "scam" in path
            print(f"[EVAL] {os.path.basename(path)} -> Risk: {res['risk_score']}% [{res['status']}]"
                  f" consensus={res.get('consensus', {}).get('verdict')}")

            self.assertIn("consensus", res)
            if is_fake:
                self.assertNotEqual(res["status"], "AUTHENTIC_HUMAN",
                                    f"{path} must never pass as authentic")
            else:
                self.assertNotEqual(res["status"], "CRITICAL_SYNTHETIC",
                                    f"{path} must never raise a false critical alarm")


class TestPreventionProtocol(unittest.TestCase):

    def test_out_of_band_otp_flow(self):
        mgr = PreventionManager()
        session_id = "SES-TEST1"

        # 1. Issue challenge
        challenge = mgr.issue_challenge(session_id, trigger_risk=94.5, reason="HiFi-GAN vocoder phase dispersion")
        self.assertEqual(challenge["session_id"], session_id)
        self.assertEqual(challenge["status"], "PENDING")
        otp = challenge["otp_code"]
        self.assertEqual(len(otp), 6)

        # 2. Verify with wrong OTP
        wrong_res = mgr.verify_challenge(session_id, "000000")
        self.assertFalse(wrong_res["success"])

        # 3. Verify with correct OTP
        valid_res = mgr.verify_challenge(session_id, otp)
        self.assertTrue(valid_res["success"])
        self.assertEqual(mgr.active_challenges[session_id]["status"], "PASSED")

        # 4. Quarantine
        q_res = mgr.quarantine_session(session_id, operator_notes="Manual kill test")
        self.assertTrue(q_res["quarantined"])


if __name__ == "__main__":
    unittest.main()
