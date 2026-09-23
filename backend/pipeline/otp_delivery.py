"""
Out-of-Band OTP Delivery Providers.

Security requirement: in a government/banking deployment the OTP must NEVER be
returned on the same channel the (possibly fraudulent) caller occupies. The
plaintext OTP travels only over the out-of-band channel (SMS to the registered
mobile, push, etc.).

Providers (select via AEGIS_OTP_DELIVERY):
  console  — dev/demo: logs the OTP and returns it in the API response so the
             demo UI can display it. NEVER use in production.
  webhook  — production-ready generic adapter: POSTs the OTP to the configured
             HTTP endpoint (AEGIS_OTP_WEBHOOK_URL) with an optional bearer token
             (AEGIS_OTP_WEBHOOK_TOKEN). Point this at an SMS gateway
             (MSG91, Twilio, government SMS relay, etc.). The OTP is NOT
             returned in the API response in this mode.
  none     — no delivery; challenge can only be verified if the operator
             delivers the OTP through an external mechanism.
"""

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger("otp-delivery")


class OtpDeliveryResult(dict):
    """{"delivered": bool, "provider": str, "detail": str, "return_otp": bool}"""


def _provider() -> str:
    return os.getenv("AEGIS_OTP_DELIVERY", "console").strip().lower()


def deliver_otp(session_id: str, otp: str,
                challenge_id: str = "") -> OtpDeliveryResult:
    """
    Sends the OTP over the configured out-of-band channel.
    Returns metadata; `return_otp=False` means the caller MUST NOT include the
    plaintext OTP in any API/WebSocket response.
    """
    provider = _provider()

    if provider == "console":
        # Dev/demo only: log it so the operator console can render it.
        logger.info(f"[DEV-OTP] session={session_id} challenge={challenge_id} otp={otp}")
        return OtpDeliveryResult(delivered=True, provider="console",
                                 detail="OTP logged for demo UI", return_otp=True)

    if provider == "webhook":
        url = os.getenv("AEGIS_OTP_WEBHOOK_URL", "").strip()
        if not url:
            logger.error("AEGIS_OTP_DELIVERY=webhook but AEGIS_OTP_WEBHOOK_URL is not set")
            return OtpDeliveryResult(delivered=False, provider="webhook",
                                     detail="Webhook URL not configured", return_otp=False)
        token = os.getenv("AEGIS_OTP_WEBHOOK_TOKEN", "").strip()
        payload: Dict[str, Any] = {
            "session_id": session_id,
            "challenge_id": challenge_id,
            "otp": otp,
            "ttl_seconds": int(os.getenv("AEGIS_CHALLENGE_TTL", "180")),
        }
        try:
            import httpx
            headers = {"Content-Type": "application/json"}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            resp = httpx.post(url, json=payload, headers=headers, timeout=10.0)
            ok = resp.status_code < 400
            return OtpDeliveryResult(
                delivered=ok, provider="webhook",
                detail=f"gateway responded {resp.status_code}" if ok
                       else f"gateway rejected ({resp.status_code})",
                return_otp=False)
        except Exception as exc:  # network failure — fail closed
            logger.error(f"OTP webhook delivery failed: {exc}")
            return OtpDeliveryResult(delivered=False, provider="webhook",
                                     detail=f"delivery error: {exc}", return_otp=False)

    if provider == "none":
        return OtpDeliveryResult(delivered=False, provider="none",
                                 detail="Delivery disabled (external mechanism)", return_otp=False)

    logger.warning(f"Unknown AEGIS_OTP_DELIVERY '{provider}' — falling back to console")
    return OtpDeliveryResult(delivered=True, provider="console",
                             detail="unknown provider fallback", return_otp=True)
