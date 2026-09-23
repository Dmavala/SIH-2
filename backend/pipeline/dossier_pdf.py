"""
Forensic Dossier PDF Export.

Renders the BSA Section 63 certificate as a print-ready PDF for law-enforcement
handoff. Uses reportlab when available; otherwise returns a styled HTML document
that browsers can print-to-PDF (keeps the endpoint dependency-optional).

The output includes the digest_basis disclosure so the document never overstates
the integrity guarantee (raw-audio hash vs telemetry fingerprint).
"""

import io
from typing import Any, Dict, Optional


def _escape(text: Any) -> str:
    s = str(text if text is not None else "")
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def render_html(certificate: Dict[str, Any]) -> str:
    """Styled, print-ready HTML rendering of the certificate."""
    header = certificate.get("legal_header", {})
    case = certificate.get("case_particulars", {})
    custody = certificate.get("chain_of_custody", {})
    findings = certificate.get("forensic_findings", {})
    anomalies = findings.get("acoustic_biometric_anomalies", [])
    signatures = findings.get("detected_signatures", [])
    charges = certificate.get("recommended_legal_charges", [])
    speech = certificate.get("speech_intelligence") or {}

    anomaly_rows = "".join(
        f"<tr><td>{_escape(a.get('metric'))}</td>"
        f"<td>{_escape(a.get('measured_value'))}</td>"
        f"<td>{_escape(a.get('normal_human_range'))}</td>"
        f"<td><b>{_escape(a.get('verdict'))}</b></td></tr>"
        for a in anomalies
    ) or "<tr><td colspan='4'>No acoustic biometric anomalies recorded.</td></tr>"

    charge_items = "".join(f"<li>{_escape(c)}</li>" for c in charges) or "<li>No charges auto-recommended.</li>"
    signature_items = "".join(f"<li>{_escape(s)}</li>" for s in signatures) or "<li>None recorded.</li>"

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>{_escape(header.get('dossier_id', 'Forensic Dossier'))}</title>
<style>
  @page {{ size: A4; margin: 18mm; }}
  body {{ font-family: Georgia, 'Times New Roman', serif; color: #111; line-height: 1.5; }}
  .seal {{ border: 2px solid #1a3a6b; padding: 14px 18px; margin-bottom: 18px; }}
  .seal h1 {{ font-size: 15px; margin: 0 0 4px; color: #1a3a6b; letter-spacing: .04em; }}
  .seal .meta {{ font-size: 11px; color: #333; }}
  h2 {{ font-size: 12px; text-transform: uppercase; letter-spacing: .08em;
       border-bottom: 1.5px solid #1a3a6b; padding-bottom: 3px; margin: 22px 0 8px; color: #1a3a6b; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
  th, td {{ border: 1px solid #999; padding: 5px 8px; text-align: left; vertical-align: top; }}
  th {{ background: #eef2f8; }}
  .attestation {{ background: #f6f4ea; border: 1px solid #cfc9a8; padding: 12px 14px; font-size: 11px; }}
  .note {{ font-size: 10px; color: #555; font-style: italic; }}
  .signblock {{ margin-top: 42px; display: flex; justify-content: space-between; font-size: 11px; }}
  .signblock div {{ width: 45%; border-top: 1px solid #111; padding-top: 5px; }}
  ul {{ font-size: 11px; }}
  .mono {{ font-family: 'Courier New', monospace; font-size: 10.5px; }}
</style></head><body>
<div class="seal">
  <h1>{_escape(header.get('title'))}</h1>
  <div class="meta">
    Dossier ID: <b class="mono">{_escape(header.get('dossier_id'))}</b> &nbsp;|&nbsp;
    Digital Seal: <span class="mono">{_escape(header.get('digital_seal'))}</span><br>
    Statutory Authority: {_escape(header.get('statutory_authority'))}<br>
    Generated (UTC): {_escape(header.get('generated_at_utc'))}
  </div>
</div>

<h2>Case Particulars</h2>
<table>
  <tr><th>Case Reference No.</th><td>{_escape(case.get('case_reference_no'))}</td></tr>
  <tr><th>FIR Reference</th><td>{_escape(case.get('fir_reference'))}</td></tr>
  <tr><th>Investigating Agency</th><td>{_escape(case.get('investigating_agency'))}</td></tr>
  <tr><th>Jurisdiction Police Station</th><td>{_escape(case.get('jurisdiction_police_station'))}</td></tr>
  <tr><th>Certifying Officer</th><td>{_escape(case.get('certifying_officer'))}</td></tr>
  <tr><th>Session Identifier</th><td class="mono">{_escape(case.get('session_identifier'))}</td></tr>
</table>

<h2>Chain of Custody</h2>
<table>
  <tr><th>Media Type</th><td>{_escape(custody.get('media_type'))}</td></tr>
  <tr><th>SHA-256 Digest</th><td class="mono">{_escape(custody.get('sha256_audio_digest'))}</td></tr>
  <tr><th>Digest Basis</th><td><b>{_escape(custody.get('digest_basis'))}</b> — {_escape(custody.get('integrity_status'))}</td></tr>
  <tr><th>Capture Methodology</th><td>{_escape(custody.get('capture_methodology'))}</td></tr>
  <tr><th>Hash Algorithm</th><td>{_escape(custody.get('hash_algorithm'))}</td></tr>
</table>
<p class="note">{_escape(custody.get('certification_note'))}</p>

<h2>Forensic Findings</h2>
<table>
  <tr><th>Composite Threat Risk</th><td>{_escape(findings.get('composite_threat_risk'))}%</td>
      <th>Classification</th><td>{_escape(findings.get('threat_classification'))}</td></tr>
  <tr><th>Synthetic Cloning Detected</th><td>{_escape(findings.get('is_synthetic_cloning_detected'))}</td>
      <th>Ensemble Consensus</th><td>{_escape(findings.get('neural_ensemble_consensus', {}))}</td></tr>
</table>
<br>
<table>
  <tr><th>Acoustic Metric</th><th>Measured</th><th>Normal Human Range</th><th>Verdict</th></tr>
  {anomaly_rows}
</table>

<h2>Detected Signatures</h2>
<ul>{signature_items}</ul>

<h2>Recommended Legal Charges</h2>
<ul>{charge_items}</ul>

{('<h2>Speech Intelligence</h2><p style="font-size:11px"><b>Transcript:</b> ' + _escape(speech.get('transcript', 'N/A'))[:2000] + '</p>') if speech else ''}

<div class="attestation">
  <b>Statutory Attestation.</b> {_escape(certificate.get('statutory_attestation'))}
</div>

<div class="signblock">
  <div>Certifying Officer (name, rank, PIS No.)</div>
  <div>Digital Signature Certificate / eSign</div>
</div>
</body></html>"""


def render_pdf_bytes(certificate: Dict[str, Any]) -> Optional[bytes]:
    """Render via reportlab if available; returns None otherwise (use render_html)."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
    except ImportError:
        return None

    header = certificate.get("legal_header", {})
    case = certificate.get("case_particulars", {})
    custody = certificate.get("chain_of_custody", {})
    findings = certificate.get("forensic_findings", {})

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    margin = 18 * mm
    y = height - margin

    def line(txt: str, font: str = "Helvetica", size: float = 9.5, dy: float = 14,
             bold: bool = False):
        nonlocal y
        c.setFont("Helvetica-Bold" if bold else font, size)
        c.drawString(margin, y, txt[:120])
        y -= dy

    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "CERTIFICATE UNDER SECTION 63, BSA 2023")
    y -= 18
    line(f"Dossier ID: {header.get('dossier_id', '')}    Seal: {header.get('digital_seal', '')}",
         size=9, dy=12)
    line(f"Authority: {header.get('statutory_authority', '')}", size=9, dy=16)

    line("CASE PARTICULARS", bold=True, dy=13)
    for k, v in [("Case No.", case.get("case_reference_no")),
                 ("FIR Ref.", case.get("fir_reference")),
                 ("Agency", case.get("investigating_agency")),
                 ("Police Station", case.get("jurisdiction_police_station")),
                 ("Certifying Officer", case.get("certifying_officer")),
                 ("Session", case.get("session_identifier"))]:
        line(f"{k}: {v}", size=9, dy=12)
    y -= 8

    line("CHAIN OF CUSTODY", bold=True, dy=13)
    line(f"Digest: {custody.get('sha256_audio_digest', '')}", size=8.5, dy=11)
    line(f"Basis: {custody.get('digest_basis', '')}", size=9, dy=11)
    line(f"Integrity: {custody.get('integrity_status', '')}", size=8.5, dy=16)

    line("FINDINGS", bold=True, dy=13)
    line(f"Composite Threat Risk: {findings.get('composite_threat_risk')}%  "
         f"Classification: {findings.get('threat_classification')}", size=9, dy=12)
    line(f"Synthetic Cloning Detected: {findings.get('is_synthetic_cloning_detected')}", size=9, dy=16)

    line("This system-generated certificate requires counter-signature by the", size=8, dy=10)
    line("certifying officer's DSC (eSign) for Section 63(4) admissibility.", size=8, dy=18)

    c.drawString(margin, 22 * mm, "Certifying Officer: ____________________")
    c.drawRightString(width - margin, 22 * mm, "DSC / eSign: ____________________")

    c.save()
    return buf.getvalue()
