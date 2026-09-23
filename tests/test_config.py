"""
Configuration module tests — env overrides and deployment validation.
"""

import os
import unittest
from unittest import mock

from backend.config import Settings, settings


class TestConfig(unittest.TestCase):

    def test_defaults_load(self):
        """Defaults hold when no AEGIS_* env overrides are present."""
        saved = {k: v for k, v in os.environ.items() if k.startswith("AEGIS_")}
        for k in saved:
            del os.environ[k]
        try:
            import importlib
            import backend.config as cfg_mod
            importlib.reload(cfg_mod)  # re-evaluate import-time defaults
            s = cfg_mod.Settings()
            self.assertEqual(s.audio.sample_rate, 16000)
            self.assertEqual(s.risk.critical, 75.0)
            self.assertEqual(s.prevention.max_otp_attempts, 3)
            self.assertEqual(s.db.backend, "sqlite")
            self.assertTrue(s.consensus.enabled)
        finally:
            os.environ.update(saved)
            import importlib
            import backend.config as cfg_mod
            importlib.reload(cfg_mod)  # restore post-override values

    def test_env_override(self):
        """
        NOTE: env values are read at import time (module-level dataclass defaults),
        so process-wide env changes require a reload of backend.config to take
        effect. This test pins down that documented behaviour.
        """
        import importlib
        from unittest import mock
        with mock.patch.dict("os.environ", {
            "AEGIS_RISK_CRITICAL": "85",
            "AEGIS_MAX_OTP_ATTEMPTS": "5",
            "AEGIS_STT_LANGUAGE": "hi-IN",
        }):
            import backend.config as cfg_mod
            importlib.reload(cfg_mod)
            try:
                self.assertEqual(cfg_mod.settings.risk.critical, 85.0)
                self.assertEqual(cfg_mod.settings.prevention.max_otp_attempts, 5)
                self.assertEqual(cfg_mod.settings.stt.language, "hi-IN")
            finally:
                importlib.reload(cfg_mod)  # restore original env-derived state

    def test_bad_env_falls_back_to_default(self):
        with mock.patch.dict("os.environ", {"AEGIS_RISK_CRITICAL": "not-a-number"}):
            s = Settings()
            self.assertEqual(s.risk.critical, 75.0)

    def _fresh_settings(self, env):
        """Reload backend.config under a patched environment."""
        import importlib
        from unittest import mock
        with mock.patch.dict("os.environ", env):
            import backend.config as cfg_mod
            importlib.reload(cfg_mod)
            try:
                return cfg_mod.Settings()
            finally:
                importlib.reload(cfg_mod)

    def test_validate_catches_prod_misconfig(self):
        s = self._fresh_settings({
            "AEGIS_ENV": "prod",
            "AEGIS_CORS_ORIGINS": "",
            "AEGIS_AUTH_ENABLED": "0",
            "AEGIS_DB_BACKEND": "memory",
            "AEGIS_RELOAD": "1",
        })
        problems = s.validate()
        self.assertTrue(any("CORS" in p for p in problems))
        self.assertTrue(any("AEGIS_AUTH_ENABLED" in p for p in problems))
        self.assertTrue(any("persist" in p for p in problems))
        self.assertTrue(any("reload" in p.lower() for p in problems))

    def test_validate_clean_prod_passes(self):
        s = self._fresh_settings({
            "AEGIS_ENV": "prod",
            "AEGIS_CORS_ORIGINS": "https://aegis.gov.in",
            "AEGIS_AUTH_ENABLED": "1",
            "AEGIS_API_KEY": "secret-key",
            "AEGIS_DB_BACKEND": "sqlite",
            "AEGIS_RELOAD": "0",
        })
        self.assertEqual(s.validate(), [])

    def test_ensemble_weight_validation(self):
        s = self._fresh_settings({
            "AEGIS_ENSEMBLE_W1": "0.9",
            "AEGIS_ENSEMBLE_W2": "0.9",
            "AEGIS_ENSEMBLE_W3": "0.9",
        })
        self.assertTrue(any("Ensemble weights" in p for p in s.validate()))

    def test_global_settings_importable(self):
        # The shared singleton must be a valid Settings instance
        self.assertIsInstance(settings, Settings)


if __name__ == "__main__":
    unittest.main()
