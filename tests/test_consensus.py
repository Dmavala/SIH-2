"""
Consensus engine tests — verdict logic, disagreement abstention, gray zone.
"""

import unittest

from backend.pipeline.consensus import resolve_consensus, VERDICT_STATUS


class TestConsensus(unittest.TestCase):

    def test_agreement_synthetic(self):
        res = resolve_consensus({"aasist": 95.0, "rawnet": 90.0})
        self.assertEqual(res["verdict"], "SYNTHETIC")
        self.assertEqual(res["confidence"], "HIGH")

    def test_agreement_authentic(self):
        res = resolve_consensus({"aasist": 10.0, "rawnet": 15.0})
        self.assertEqual(res["verdict"], "AUTHENTIC")
        self.assertEqual(res["confidence"], "HIGH")

    def test_disagreement_abstains(self):
        res = resolve_consensus({"aasist": 97.0, "rawnet": 13.0})
        self.assertEqual(res["verdict"], "INCONCLUSIVE")
        self.assertEqual(res["confidence"], "LOW")
        self.assertIn("disagreement", res["reason"].lower())
        self.assertGreater(res["spread"], 30)

    def test_gray_zone_abstains(self):
        res = resolve_consensus({"aasist": 55.0, "rawnet": 50.0})
        self.assertEqual(res["verdict"], "INCONCLUSIVE")
        self.assertEqual(res["confidence"], "MEDIUM")

    def test_single_engine_flagged(self):
        res = resolve_consensus({"aasist": 90.0})
        self.assertEqual(res["verdict"], "SYNTHETIC")
        self.assertEqual(res["confidence"], "SINGLE_ENGINE")

    def test_single_engine_gray(self):
        res = resolve_consensus({"rawnet": 50.0})
        self.assertEqual(res["verdict"], "INCONCLUSIVE")

    def test_empty_scores(self):
        res = resolve_consensus({})
        self.assertEqual(res["verdict"], "INCONCLUSIVE")

    def test_boundary_exactly_at_thresholds(self):
        # mean exactly 70 -> SYNTHETIC (>=)
        res = resolve_consensus({"a": 70.0, "b": 70.0})
        self.assertEqual(res["verdict"], "SYNTHETIC")
        # mean exactly 35 -> AUTHENTIC (<=)
        res = resolve_consensus({"a": 35.0, "b": 35.0})
        self.assertEqual(res["verdict"], "AUTHENTIC")

    def test_status_mapping_covers_all_verdicts(self):
        for verdict in ("SYNTHETIC", "AUTHENTIC", "INCONCLUSIVE"):
            self.assertIn(verdict, VERDICT_STATUS)


if __name__ == "__main__":
    unittest.main()
