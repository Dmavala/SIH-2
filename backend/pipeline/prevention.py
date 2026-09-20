"""
Prevention & Out-of-Band Challenge Layer (Crucial for SIH).

When a voice clone or synthetic speech is detected during a live VoIP or banking call:
1. Triggers real-time threat alert (Risk > 85%).
2. Freezes sensitive actions (e.g. wire transfer, account credential change).
3. Automatically triggers Out-of-Band (OOB) secondary channel challenge (OTP / Push).
4. Maintains audit log of forensic incidents.
"""

import time
import random
import uuid
from typing import Dict, Any, List, Optional


class ThreatAggregator:
    """
    Maintains a temporal moving window of risk scores to avoid single-frame false alarms
    while reacting quickly (< 1.5 seconds) to sustained synthetic voice attacks.
    """

    def __init__(self, window_size: int = 4, threshold_critical: float = 80.0):
        self.window_size = window_size
        self.threshold_critical = threshold_critical
        self.history: List[float] = []

    def update(self, current_risk: float, is_idle: bool = False) -> float:
        if is_idle:
            if not self.history:
                return 0.0
            # During short conversational pause, hold previous state with smooth decay
            decayed = max(0.0, self.history[-1] * 0.90)
            self.history.append(decayed)
            if len(self.history) > self.window_size:
                self.history.pop(0)
            return round(decayed, 1)

        self.history.append(current_risk)
        if len(self.history) > self.window_size:
            self.history.pop(0)

        # Exponentially weighted moving average giving higher weight to latest frames
        weights = [1.2 ** i for i in range(len(self.history))]
        weighted_avg = sum(w * r for w, r in zip(weights, self.history)) / sum(weights)
        return round(weighted_avg, 1)

    def reset(self):
        self.history.clear()


class PreventionManager:
    """
    Manages in-call prevention protocols, active challenges, and forensic audit logs in-memory.
    """

    def __init__(self):
        self.active_challenges: Dict[str, Dict[str, Any]] = {}
        self.audit_log: List[Dict[str, Any]] = []

    def issue_challenge(self, session_id: str, trigger_risk: float, reason: str) -> Dict[str, Any]:
        """
        Generates an Out-of-Band OTP challenge for the session.
        """
        otp = f"{random.randint(100000, 999999)}"
        challenge_id = f"CHAL-{uuid.uuid4().hex[:8].upper()}"
        challenge_record = {
            "challenge_id": challenge_id,
            "session_id": session_id,
            "otp_code": otp,
            "status": "PENDING",
            "trigger_risk": trigger_risk,
            "reason": reason,
            "created_at": time.time(),
            "expires_at": time.time() + 180,  # 3 minutes expiry
        }
        self.active_challenges[session_id] = challenge_record

        # Log incident
        self.log_event(
            event_type="DEFENSE_TRIGGERED",
            session_id=session_id,
            details=f"Threat score reached {trigger_risk}%. Out-of-band challenge {challenge_id} initiated. Call frozen.",
            severity="CRITICAL",
        )

        return challenge_record

    def verify_challenge(self, session_id: str, submitted_otp: str) -> Dict[str, Any]:
        """
        Verifies caller's OTP submission.
        """
        challenge = self.active_challenges.get(session_id)
        if not challenge:
            return {"success": False, "message": "No active challenge found for this session"}

        if time.time() > challenge["expires_at"]:
            challenge["status"] = "EXPIRED"
            self.log_event(
                event_type="CHALLENGE_EXPIRED",
                session_id=session_id,
                details="Out-of-band OTP expired.",
                severity="WARNING",
            )
            return {"success": False, "message": "Challenge has expired. Please re-authenticate."}

        if submitted_otp.strip() == challenge["otp_code"]:
            challenge["status"] = "PASSED"
            self.log_event(
                event_type="CHALLENGE_VERIFIED",
                session_id=session_id,
                details="Caller verified identity via out-of-band channel. Threat mitigated for session.",
                severity="INFO",
            )
            return {"success": True, "message": "Identity verified successfully. Call actions unlocked."}
        else:
            challenge["status"] = "FAILED"
            self.log_event(
                event_type="CHALLENGE_FAILED",
                session_id=session_id,
                details="Invalid OTP entered for session. Potential voice spoof attack confirmed.",
                severity="CRITICAL",
            )
            return {"success": False, "message": "Invalid OTP code. Authentication rejected."}

    def quarantine_session(self, session_id: str, operator_notes: str = "") -> Dict[str, Any]:
        """
        Immediately isolates and terminates/mutes a compromised voice line.
        """
        self.log_event(
            event_type="LINE_QUARANTINED",
            session_id=session_id,
            details=f"Operator terminated voice line. Notes: {operator_notes}",
            severity="CRITICAL",
        )
        if session_id in self.active_challenges:
            self.active_challenges[session_id]["status"] = "QUARANTINED"
        return {"session_id": session_id, "quarantined": True, "timestamp": time.time()}

    def log_event(self, event_type: str, session_id: str, details: str, severity: str = "INFO"):
        event = {
            "id": f"EVT-{uuid.uuid4().hex[:6].upper()}",
            "timestamp": time.time(),
            "time_str": time.strftime("%H:%M:%S"),
            "event_type": event_type,
            "session_id": session_id,
            "details": details,
            "severity": severity,
        }
        self.audit_log.insert(0, event)
        if len(self.audit_log) > 100:
            self.audit_log.pop()

    def get_audit_log(self) -> List[Dict[str, Any]]:
        return self.audit_log

