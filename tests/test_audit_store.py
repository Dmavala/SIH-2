"""
Evidence store tests — hash-chain integrity, tamper detection, challenge
persistence, and dossier storage.
"""

import os
import sqlite3
import tempfile
import time
import unittest

from backend.pipeline.audit_store import AuditStore
from backend.pipeline.prevention import PreventionManager, ThreatAggregator


class TestAuditStore(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.store = AuditStore(os.path.join(self._tmp.name, "evidence.db"))

    def test_chain_is_valid_after_writes(self):
        for i in range(10):
            self.store.log_event("TEST_EVENT", f"SES-{i}", f"details {i}")
        report = self.store.verify_chain()
        self.assertTrue(report["valid"])
        self.assertEqual(report["events"], 10)

    def test_tampering_breaks_chain(self):
        for i in range(5):
            self.store.log_event("TEST_EVENT", f"SES-{i}", f"details {i}")
        # Simulate direct DB modification (attacker editing history)
        db_path = self.store.db_path
        conn = sqlite3.connect(db_path)
        conn.execute("UPDATE audit_events SET details='ALTERED HISTORY' WHERE id=2")
        conn.commit()
        conn.close()
        report = self.store.verify_chain()
        self.assertFalse(report["valid"])
        self.assertIn("reason", report)

    def test_log_event_has_hash_fields(self):
        ev = self.store.log_event("X", "S", "d")
        self.assertIn("entry_hash", ev)
        self.assertIn("prev_hash", ev)
        self.assertEqual(len(ev["entry_hash"]), 64)  # sha256 hex

    def test_audit_log_ordering(self):
        self.store.log_event("FIRST", "S", "d1")
        time.sleep(0.01)
        self.store.log_event("SECOND", "S", "d2")
        log = self.store.get_audit_log(limit=10)
        self.assertEqual(log[0]["event_type"], "SECOND")  # newest first
        self.assertEqual(log[-1]["event_type"], "FIRST")

    def test_challenge_persistence_roundtrip(self):
        rec = {"challenge_id": "C1", "status": "PENDING", "otp_hash": "x" * 64}
        self.store.save_challenge("SES-A", rec)
        loaded = self.store.load_challenge("SES-A")
        self.assertEqual(loaded["challenge_id"], "C1")
        # Update overwrites
        rec["status"] = "PASSED"
        self.store.save_challenge("SES-A", rec)
        self.assertEqual(self.store.load_challenge("SES-A")["status"], "PASSED")

    def test_dossier_storage(self):
        self.store.save_dossier("D-1", "SES-A", {"legal_header": {"dossier_id": "D-1"}})
        got = self.store.get_dossier("D-1")
        self.assertIsNotNone(got)
        self.assertEqual(got["legal_header"]["dossier_id"], "D-1")
        self.assertIsNone(self.store.get_dossier("MISSING"))

    def test_memory_mode(self):
        m = AuditStore(":memory:")
        m.log_event("A", "S1", "x")
        m.log_event("B", "S2", "y")
        self.assertTrue(m.verify_chain()["valid"])
        self.assertEqual(len(m.get_audit_log()), 2)


class TestPreventionDurability(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.db_path = os.path.join(self._tmp.name, "evidence.db")
        self.mgr = PreventionManager(store=AuditStore(self.db_path))

    def test_otp_not_stored_in_plaintext(self):
        ch = self.mgr.issue_challenge("SES-1", 90.0, "test reason")
        self.assertIn("otp_code", ch)  # returned once for delivery
        import json
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT record FROM challenges WHERE session_id='SES-1'").fetchone()
        conn.close()
        stored = json.loads(row[0])
        self.assertNotIn("otp_code", stored)
        self.assertNotEqual(stored.get("otp_hash", ""), ch["otp_code"])
        self.assertIn("otp_salt", stored)

    def test_lockout_after_max_attempts(self):
        ch = self.mgr.issue_challenge("SES-2", 90.0, "test")
        for i in range(ch["max_attempts"]):
            res = self.mgr.verify_challenge("SES-2", "000000")
            self.assertFalse(res["success"])
            if i < ch["max_attempts"] - 1:
                self.assertFalse(res.get("locked", False))
        # Now locked: even the correct OTP is rejected
        res = self.mgr.verify_challenge("SES-2", ch["otp_code"])
        self.assertFalse(res["success"])
        self.assertTrue(res.get("locked", False))

    def test_correct_otp_passes(self):
        ch = self.mgr.issue_challenge("SES-3", 90.0, "test")
        res = self.mgr.verify_challenge("SES-3", ch["otp_code"])
        self.assertTrue(res["success"])
        self.assertEqual(self.mgr.active_challenges["SES-3"]["status"], "PASSED")

    def test_expired_challenge_rejected(self):
        ch = self.mgr.issue_challenge("SES-4", 90.0, "test")
        # Force expiry
        self.mgr.active_challenges["SES-4"]["expires_at"] = time.time() - 1
        res = self.mgr.verify_challenge("SES-4", ch["otp_code"])
        self.assertFalse(res["success"])
        self.assertIn("expired", res["message"].lower())

    def test_unknown_session_rejected(self):
        res = self.mgr.verify_challenge("NOPE", "123456")
        self.assertFalse(res["success"])

    def test_audit_events_persist_across_restart(self):
        self.mgr.issue_challenge("SES-5", 90.0, "restart test")
        self.mgr.quarantine_session("SES-5", "operator kill")
        # "Restart": new manager instance over same DB
        mgr2 = PreventionManager(store=AuditStore(self.db_path))
        log = mgr2.get_audit_log()
        types = [e["event_type"] for e in log]
        self.assertIn("DEFENSE_TRIGGERED", types)
        self.assertIn("LINE_QUARANTINED", types)
        self.assertTrue(mgr2.verify_chain()["valid"])


class TestThreatAggregator(unittest.TestCase):

    def test_empty_history_idle(self):
        agg = ThreatAggregator()
        self.assertEqual(agg.update(0.0, is_idle=True), 0.0)

    def test_ewma_weights_recent_frames(self):
        agg = ThreatAggregator()
        r1 = agg.update(20.0)
        r2 = agg.update(90.0)
        self.assertGreater(r2, 50.0)  # recent spike dominates

    def test_pause_hold_keeps_alert_during_silence(self):
        agg = ThreatAggregator()
        for _ in range(5):
            agg.update(90.0)
        held = agg.update(0.0, is_idle=True)
        self.assertGreater(held, 70.0)  # alert survives conversational pause

    def test_reset(self):
        agg = ThreatAggregator()
        agg.update(90.0)
        agg.reset()
        self.assertEqual(agg.history, [])
        self.assertEqual(agg.peak_risk, 0.0)


if __name__ == "__main__":
    unittest.main()
