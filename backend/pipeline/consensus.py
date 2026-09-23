"""
Multi-Model Consensus Engine.

Rationale (forensic-grade requirement):
  A detection system used for legal action must NEVER output a confident verdict
  when its own engines disagree. Measured on this repo's own demo set, AASIST and
  RawNet2 occasionally diverge by >90 points (e.g. 97.4% vs 12.8% on the same
  authentic telephony sample). Shipping a single-engine verdict in that situation
  produces confident wrong answers — unacceptable for MHA/I4C/RBI workflows.

Policy:
  - One engine only  -> pass through (flagged as low-confidence single engine).
  - Engines agree    -> verdict from the mean score (SYNTHETIC / AUTHENTIC /
                        GRAY ZONE => INCONCLUSIVE).
  - Engines disagree beyond AEGIS_CONSENSUS_DISAGREEMENT -> INCONCLUSIVE with an
    explicit human-review escalation reason.
"""

from typing import Any, Dict, Optional

from backend.config import settings


def resolve_consensus(scores: Dict[str, float],
                      forensics: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Args:
        scores: mapping engine-name -> risk score in percent (0-100).
        forensics: optional acoustic forensics dict (included in the output for the dossier).

    Returns:
        {
          "verdict": "SYNTHETIC" | "AUTHENTIC" | "INCONCLUSIVE",
          "mean_score": float,
          "spread": float,
          "scores": {engine: score},
          "confidence": "HIGH" | "MEDIUM" | "LOW" | "SINGLE_ENGINE",
          "reason": str,
        }
    """
    c = settings.consensus
    clean = {k: float(v) for k, v in scores.items() if v is not None}
    scores_out = {k: round(v, 2) for k, v in clean.items()}

    if not clean:
        return {
            "verdict": "INCONCLUSIVE", "mean_score": 0.0, "spread": 0.0,
            "scores": {}, "confidence": "LOW",
            "reason": "No engine produced a score.",
        }

    if len(clean) == 1:
        (engine, score), = clean.items()
        verdict = "SYNTHETIC" if score >= c.fake_threshold else (
            "AUTHENTIC" if score <= c.real_threshold else "INCONCLUSIVE")
        return {
            "verdict": verdict, "mean_score": round(score, 2), "spread": 0.0,
            "scores": scores_out, "confidence": "SINGLE_ENGINE",
            "reason": f"Single-engine verdict ({engine}); enable multi-model consensus for corroboration.",
        }

    mean = sum(clean.values()) / len(clean)
    spread = max(clean.values()) - min(clean.values())

    # Weighted fusion score (env-tunable engine weights, normalized internally)
    raw_w = {"aasist": c.weight_aasist, "rawnet": c.weight_rawnet}
    w = {k: raw_w.get(k, 0.0) for k in clean}
    total_w = sum(w.values())
    if total_w <= 0:
        w = {k: 1.0 / len(clean) for k in clean}
        total_w = 1.0
    fused = sum(clean[k] * (w[k] / total_w) for k in clean)

    if spread > c.disagreement_margin:
        detail = ", ".join(f"{k}={v:.1f}%" for k, v in sorted(clean.items()))
        return {
            "verdict": "INCONCLUSIVE", "mean_score": round(fused, 2),
            "spread": round(spread, 2), "scores": scores_out,
            "confidence": "LOW",
            "reason": (f"Engine disagreement ({detail}) exceeds {c.disagreement_margin:.0f}pt "
                       f"margin — escalate to human analyst."),
        }

    if fused >= c.fake_threshold:
        verdict, confidence, reason = "SYNTHETIC", "HIGH", "Engines agree audio is synthetic."
    elif fused <= c.real_threshold:
        verdict, confidence, reason = "AUTHENTIC", "HIGH", "Engines agree audio is authentic."
    else:
        verdict, confidence, reason = ("INCONCLUSIVE", "MEDIUM",
                                       "Fused score in gray zone — human review advised.")

    return {
        "verdict": verdict, "mean_score": round(fused, 2), "spread": round(spread, 2),
        "scores": scores_out, "confidence": confidence, "reason": reason,
    }


# Status/color vocabulary shared with the frontend
VERDICT_STATUS = {
    "SYNTHETIC": "CRITICAL_SYNTHETIC",
    "AUTHENTIC": "AUTHENTIC_HUMAN",
    "INCONCLUSIVE": "INCONCLUSIVE",
}
VERDICT_COLOR = {
    "SYNTHETIC": "red",
    "AUTHENTIC": "green",
    "INCONCLUSIVE": "amber",
}
VERDICT_LABEL = {
    "SYNTHETIC": "SYNTHETIC VOICE DETECTED (ENSEMBLE CONSENSUS)",
    "AUTHENTIC": "AUTHENTIC HUMAN BIOMETRICS (ENSEMBLE CONSENSUS)",
    "INCONCLUSIVE": "ENGINES DISAGREE / GRAY ZONE — HUMAN REVIEW REQUIRED",
}
