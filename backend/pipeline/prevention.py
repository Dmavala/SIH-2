"""
Prevention & Out-of-Band Challenge Layer.

When a voice clone or synthetic speech is detected during a live VoIP or banking call:
1. Triggers real-time threat alert (configurable thresholds).
2. Freezes sensitive actions (e.g. wire transfer, account credential change).
3. Automatically triggers Out-of-Band (OOB) secondary channel challenge (OTP / Push).
4. Maintains a durable, tamper-evident audit log (SQLite hash chain).

Evidence-grade behaviour:
- OTPs are stored only as salted SHA-256 hashes (never plaintext) so a leaked
  database cannot be used to pass pending challenges.
- Challenge state survives process restarts (persisted via AuditStore).
- All state transitions emit chained audit events.
"""

import hashlib
import json
import secrets
import time
import uuid
from typing import Dict, Any, List, Optional

from backend.config import settings
from backend.pipeline.audit_store import AuditStore
from backend.pipeline.otp_delivery import deliver_otp


def _hash_otp(otp: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{otp}".encode("utf-8")).hexdigest()


class ThreatAggregator:
    """
    Maintains a temporal moving window of risk scores to avoid single-frame false alarms
    while reacting quickly (< 1.5 seconds) to sustained synthetic voice attacks.
    Includes temporal hysteresis and conversational pause peak-hold so alerts do not
    prematurely collapse to 0% during natural speech pauses. Dynamics are config-driven.
    """

    def __init__(self, window_size: Optional[int] = None,
                 threshold_critical: Optional[float] = None):
        self.window_size = window_size or settings.prevention.threat_window
        self.threshold_critical = (threshold_critical
                                   if threshold_critical is not None
                                   else settings.prevention.threat_threshold_critical)
        self.history: List[float] = []
        self.peak_risk: float = 0.0
        self.idle_frames_count: int = 0
        self.max_idle_hold_frames: int = settings.prevention.idle_hold_frames

    def update(self, current_risk: float, is_idle: bool = False) -> float:
        p = settings.prevention
        if is_idle:
            self.idle_frames_count += 1
            if not self.history:
                return 0.0

            # Conversational pause peak-hold: keep alert state during natural pauses
            if (self.peak_risk >= p.peak_hold_floor
                    and self.idle_frames_count <= self.max_idle_hold_frames):
                held_score = max(0.0, self.history[-1] * p.idle_hold_decay)
                self.history.append(held_score)
                if len(self.history) > self.window_size:
                    self.history.pop(0)
                return round(held_score, 1)

            # Beyond grace period or low initial threat: smooth gentle decay
            decayed = max(0.0, self.history[-1] * p.idle_decay)
            self.peak_risk = max(0.0, self.peak_risk * p.idle_peak_decay)
            self.history.append(decayed)
            if len(self.history) > self.window_size:
                self.history.pop(0)
            return round(decayed, 1)

        # Active speech detected: reset idle frame counter
        self.idle_frames_count = 0
        if current_risk > self.peak_risk:
            self.peak_risk = current_risk
        else:
            # Gradually blend peak towards current risk
            self.peak_risk = p.peak_blend_keep * self.peak_risk + (1 - p.peak_blend_keep) * current_risk

        self.history.append(current_risk)
        if len(self.history) > self.window_size:
            self.history.pop(0)

        # Exponentially weighted moving average giving higher weight to latest frames
        weights = [p.ewma_base ** i for i in range(len(self.history))]
        weighted_avg = sum(w * r for w, r in zip(weights, self.history)) / sum(weights)
        return round(weighted_avg, 1)

    def reset(self):
        self.history.clear()
        self.peak_risk = 0.0
        self.idle_frames_count = 0


class PreventionManager:
    """
    Manages in-call prevention protocols, active challenges, and forensic audit
    logging with durable, tamper-evident storage (SQLite hash chain).
    """

    def __init__(self, store: Optional[AuditStore] = None):
        self.store = store or AuditStore()
        # Hydrate active challenges from the durable store (survives restarts)
        self.active_challenges: Dict[str, Dict[str, Any]] = self.store.list_active_challenges()
        # Fast in-memory tail of the audit log for the dashboard (source of truth = store)
        self._recent: List[Dict[str, Any]] = self.store.get_audit_log(
            limit=settings.prevention.audit_log_size)

    # ------------------------------------------------------------------ audit
    def log_event(self, event_type: str, session_id: str, details: str,
                  severity: str = "INFO") -> Dict[str, Any]:
        event = self.store.log_event(event_type, session_id, details, severity)
        self._recent.insert(0, event)
        if len(self._recent) > settings.prevention.audit_log_size:
            self._recent.pop()
        return event

    def get_audit_log(self) -> List[Dict[str, Any]]:
        # Read-through from the store so multiple workers see the same trail
        self._recent = self.store.get_audit_log(limit=settings.prevention.audit_log_size)
        return self._recent

    def verify_chain(self) -> Dict[str, Any]:
        return self.store.verify_chain()

    # -------------------------------------------------------------- challenges
    def issue_challenge(self, session_id: str, trigger_risk: float, reason: str) -> Dict[str, Any]:
        """
        Generates an Out-of-Band OTP challenge for the session.
        The OTP itself is returned once to be delivered via the out-of-band
        channel (SMS gateway); only its salted hash is persisted.
        """
        otp = "".join(secrets.choice("0123456789") for _ in range(settings.prevention.otp_length))
        salt = secrets.token_hex(8)
        challenge_id = f"CHAL-{uuid.uuid4().hex[:8].upper()}"
        challenge_record = {
            "challenge_id": challenge_id,
            "session_id": session_id,
            # NOTE: otp_hash + otp_salt persisted; plaintext OTP is NOT stored.
            "otp_hash": _hash_otp(otp, salt),
            "otp_salt": salt,
            "status": "PENDING",
            "trigger_risk": trigger_risk,
            "reason": reason,
            "attempts": 0,
            "max_attempts": settings.prevention.max_otp_attempts,
            "created_at": time.time(),
            "expires_at": time.time() + settings.prevention.challenge_ttl_seconds,
        }
        self.active_challenges[session_id] = challenge_record
        self.store.save_challenge(session_id, challenge_record)

        # Out-of-band delivery: the plaintext OTP leaves ONLY via the configured
        # provider (SMS gateway in prod). In webhook/none mode it is never
        # returned on the in-call channel.
        delivery = deliver_otp(session_id, otp, challenge_id)

        self.log_event(
            event_type="DEFENSE_TRIGGERED",
            session_id=session_id,
            details=(f"Threat score reached {trigger_risk}%. Out-of-band challenge "
                     f"{challenge_id} initiated. Call frozen. "
                     f"OTP delivery via {delivery['provider']}: {delivery['detail']}."),
            severity="CRITICAL",
        )

        response = dict(challenge_record)
        response["otp_delivery"] = {
            "provider": delivery["provider"],
            "delivered": delivery["delivered"],
            "detail": delivery["detail"],
        }
        if delivery["return_otp"]:
            response["otp_code"] = otp  # console/demo mode only
        return response

    def verify_challenge(self, session_id: str, submitted_otp: str) -> Dict[str, Any]:
        """
        Verifies caller's OTP submission with TTL and brute-force lockout.
        Multi-worker safe: state is read through from the evidence store so any
        uvicorn worker can verify a challenge issued by another worker.
        """
        challenge = self.active_challenges.get(session_id)
        if not challenge:
            challenge = self.store.load_challenge(session_id)
        if not challenge:
            return {"success": False, "message": "No active challenge found for this session"}
        # Rehydrate the local cache with the authoritative store state
        self.active_challenges[session_id] = challenge

        if time.time() > challenge["expires_at"]:
            challenge["status"] = "EXPIRED"
            self.store.save_challenge(session_id, challenge)
            self.log_event(
                event_type="CHALLENGE_EXPIRED",
                session_id=session_id,
                details="Out-of-band OTP expired.",
                severity="WARNING",
            )
            return {"success": False, "message": "Challenge has expired. Please re-authenticate."}

        if challenge.get("attempts", 0) >= challenge.get("max_attempts",
                                                         settings.prevention.max_otp_attempts):
            challenge["status"] = "LOCKED"
            self.store.save_challenge(session_id, challenge)
            self.log_event(
                event_type="CHALLENGE_LOCKED",
                session_id=session_id,
                details="Maximum OTP attempts exhausted. Challenge locked; quarantine recommended.",
                severity="CRITICAL",
            )
            return {"success": False, "message": "Too many failed attempts. Challenge locked.",
                    "locked": True}

        if _hash_otp(submitted_otp.strip(), challenge["otp_salt"]) == challenge["otp_hash"]:
            challenge["status"] = "PASSED"
            self.store.save_challenge(session_id, challenge)
            self.log_event(
                event_type="CHALLENGE_VERIFIED",
                session_id=session_id,
                details="Caller verified identity via out-of-band channel. Threat mitigated for session.",
                severity="INFO",
            )
            return {"success": True, "message": "Identity verified successfully. Call actions unlocked."}

        challenge["attempts"] = challenge.get("attempts", 0) + 1
        remaining = max(0, challenge["max_attempts"] - challenge["attempts"])
        challenge["status"] = "FAILED" if remaining > 0 else "LOCKED"
        self.store.save_challenge(session_id, challenge)
        self.log_event(
            event_type="CHALLENGE_FAILED",
            session_id=session_id,
            details=f"Invalid OTP entered for session ({remaining} attempt(s) remaining).",
            severity="CRITICAL" if remaining == 0 else "WARNING",
        )
        msg = (f"Invalid OTP code. {remaining} attempt(s) remaining."
               if remaining > 0 else "Invalid OTP code. Challenge locked.")
        return {"success": False, "message": msg, "locked": remaining == 0}

    def quarantine_session(self, session_id: str, operator_notes: str = "") -> Dict[str, Any]:
        """Immediately isolates and terminates/mutes a compromised voice line."""
        self.log_event(
            event_type="LINE_QUARANTINED",
            session_id=session_id,
            details=f"Operator terminated voice line. Notes: {operator_notes}",
            severity="CRITICAL",
        )
        if session_id in self.active_challenges:
            self.active_challenges[session_id]["status"] = "QUARANTINED"
            self.store.save_challenge(session_id, self.active_challenges[session_id])
        return {"session_id": session_id, "quarantined": True, "timestamp": time.time()}

    def resolve_challenge(self, session_id: str, reason: str = "Operator dismissed or verified challenge") -> None:
        """Cleans and dismisses active challenge from both in-memory cache and durable store."""
        challenge = self.active_challenges.pop(session_id, None)
        if not challenge:
            challenge = self.store.load_challenge(session_id)
        if challenge:
            challenge["status"] = "DISMISSED"
            self.store.save_challenge(session_id, challenge)
            self.log_event(
                event_type="CHALLENGE_DISMISSED",
                session_id=session_id,
                details=f"Challenge dismissed or verified: {reason}. Session reset to baseline.",
                severity="INFO",
            )

