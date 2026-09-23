"""
API endpoint tests — security middleware, traversal guard, dossier export,
audit chain endpoint, and rate limiting behaviour.
"""

import os
import tempfile
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from backend.pipeline.audit_store import AuditStore
from backend.pipeline.prevention import PreventionManager
from backend.config import settings


class ApiTestBase(unittest.TestCase):
    """Base: build a fresh app state against a temp evidence DB."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        db_path = os.path.join(self._tmp.name, "evidence.db")
        # Rebind the module-level singletons to an isolated store
        import backend.main as main_mod
        self.main_mod = main_mod
        store = AuditStore(db_path)
        main_mod.evidence_store = store
        main_mod.prevention_manager = PreventionManager(store=store)
        self.client = TestClient(main_mod.app)


class TestPublicEndpoints(ApiTestBase):

    def test_health(self):
        r = self.client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "HEALTHY")

    def test_samples_only_existing_files(self):
        r = self.client.get("/api/samples")
        self.assertEqual(r.status_code, 200)
        for item in r.json():
            self.assertTrue(
                os.path.exists(os.path.join(settings.paths.samples_dir, item["filename"])))

    def test_audit_log_and_chain(self):
        self.main_mod.prevention_manager.log_event("API_TEST", "SES-X", "hello")
        r = self.client.get("/api/audit-log")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(any(e["event_type"] == "API_TEST" for e in r.json()))
        r = self.client.get("/api/audit-verify")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["valid"])

    def test_audio_traversal_blocked(self):
        r = self.client.get("/api/audio/..%2F..%2Fmain.py")
        self.assertIn(r.status_code, (400, 404))
        r = self.client.get("/api/audio/internal_config.txt")
        self.assertIn(r.status_code, (400, 404))  # non-wav rejected


class TestDossierEndpoints(ApiTestBase):

    def test_generate_and_export(self):
        payload = {
            "session_id": "SES-TEST",
            "threat_score": 91.0,
            "status": "CRITICAL_SYNTHETIC",
            "forensics": {"jitter_local": 0.002, "ambient_noise_floor_db": -80,
                          "phase_dispersion": 0.05},
            "anomalies": ["Test anomaly"],
        }
        r = self.client.post("/api/generate-dossier", json=payload)
        self.assertEqual(r.status_code, 200)
        cert = r.json()
        dossier_id = cert["legal_header"]["dossier_id"]

        # Persisted & retrievable
        r2 = self.client.get(f"/api/dossiers/{dossier_id}")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["legal_header"]["dossier_id"], dossier_id)

        # Export HTML (reportlab may or may not be installed; HTML fallback covers both)
        r3 = self.client.get(f"/api/dossiers/{dossier_id}/export?format=html")
        self.assertEqual(r3.status_code, 200)
        self.assertIn("SECTION 63", r3.text.upper())

    def test_dossier_discloses_digest_basis(self):
        payload = {
            "session_id": "SES-DIG",
            "threat_score": 91.0,
            "status": "CRITICAL_SYNTHETIC",
            "forensics": {},
        }
        cert = self.client.post("/api/generate-dossier", json=payload).json()
        basis = cert["chain_of_custody"]["digest_basis"]
        self.assertIn("TELEMETRY", basis)  # no raw audio supplied -> must NOT claim audio hash


class TestSecurityMiddleware(ApiTestBase):

    def test_auth_enabled_blocks_missing_key(self):
        with mock.patch.object(settings.auth, "enabled", True), \
             mock.patch.object(settings.auth, "api_key", "k3y"):
            r = self.client.get("/api/set-model")  # non-exempt path
            self.assertEqual(r.status_code, 401)
            r2 = self.client.get("/api/health", headers={"X-API-Key": "k3y"})
            self.assertEqual(r2.status_code, 200)  # exempt path

    def test_rate_limit_on_otp_endpoint(self):
        with mock.patch.object(settings.rate_limit, "enabled", True), \
             mock.patch.object(settings.rate_limit, "otp_verify_per_minute", 3):
            codes = []
            for _ in range(6):
                r = self.client.post("/api/verify-otp",
                                     json={"session_id": "X", "otp_code": "000000"})
                codes.append(r.status_code)
            self.assertIn(429, codes)

    def test_set_model_validation(self):
        r = self.client.post("/api/set-model", json={"model": "GARBAGE"})
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
