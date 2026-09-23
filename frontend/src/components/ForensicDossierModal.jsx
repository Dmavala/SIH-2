import React, { useEffect } from 'react';
import { Shield, FileCheck, Download, Printer, X, AlertTriangle, Scale, Lock, Hash, MessageSquare, Sparkles, Quote } from 'lucide-react';

export default function ForensicDossierModal({
  isOpen,
  dossier,
  onClose,
}) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen || !dossier) return null;

  const handlePrint = () => {
    window.print();
  };

  const handleDownloadJson = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(dossier, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `${dossier.legal_header?.dossier_id || 'forensic_dossier'}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const header = dossier.legal_header || {};
  const caseData = dossier.case_particulars || {};
  const custody = dossier.chain_of_custody || {};
  const findings = dossier.forensic_findings || {};
  const charges = dossier.recommended_legal_charges || [];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby="dossier-title"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-4xl bg-white border border-slate-200 rounded-3xl shadow-2xl overflow-hidden my-8 text-slate-800"
        onClick={(e) => e.stopPropagation()}
      >
        
        {/* Top Action Bar (hidden in print) */}
        <div className="flex items-center justify-between px-6 md:px-8 py-4 border-b border-slate-200 bg-slate-50 print:hidden">
          <div className="flex items-center gap-2.5 text-sm text-slate-800 font-bold">
            <Scale className="w-5 h-5 text-slate-700" />
            <span id="dossier-title">Section 63 BSA 2023 Forensic Evidence Certificate</span>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handlePrint}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold bg-slate-900 hover:bg-slate-800 text-white transition shadow-xs min-h-[40px] cursor-pointer"
              title="Print official court certificate"
              aria-label="Print official court certificate"
            >
              <Printer className="w-4 h-4" /> Print Certificate
            </button>
            <button
              onClick={handleDownloadJson}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold bg-white hover:bg-slate-50 border border-slate-200 text-slate-800 transition shadow-2xs min-h-[40px] cursor-pointer"
              title="Download cryptographic evidence JSON"
              aria-label="Download cryptographic evidence JSON"
            >
              <Download className="w-4 h-4 text-slate-500" /> Export JSON
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition min-w-[40px] min-h-[40px] flex items-center justify-center cursor-pointer"
              aria-label="Close certificate modal"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Printable Official Government Document Body */}
        <div className="p-8 md:p-10 space-y-7 text-sm bg-white">
          
          {/* Government Emblem & Header */}
          <div className="text-center border-b border-slate-200 pb-6">
            <div className="flex justify-center mb-3">
              <div className="p-3.5 rounded-full bg-slate-100 border border-slate-200 text-slate-800">
                <Shield className="w-8 h-8" />
              </div>
            </div>
            <h1 className="text-lg font-extrabold tracking-wider text-slate-900 uppercase m-0">
              Government of India • Ministry of Home Affairs (MHA)
            </h1>
            <h2 className="text-xs text-slate-500 tracking-wider uppercase mt-1 font-semibold">
              Indian Cyber Crime Coordination Centre (I4C) • Cyber Forensics & Anti-Fraud Division
            </h2>
            <div className="mt-4 inline-block px-5 py-2 rounded-xl border border-slate-300 bg-slate-100 text-slate-900 text-xs font-bold tracking-wide">
              {header.title || "CERTIFICATE UNDER SECTION 63 OF BHARATIYA SAKSHYA ADHINIYAM (BSA), 2023"}
            </div>
            <div className="mt-4 text-xs text-slate-500 flex flex-wrap justify-center gap-6 font-medium">
              <span>Dossier ID: <strong className="text-slate-900 font-mono">{header.dossier_id}</strong></span>
              <span>Digital Seal: <strong className="text-slate-900 font-mono">{header.digital_seal}</strong></span>
              <span>Generated: <strong className="text-slate-900">{header.generated_at_utc}</strong></span>
            </div>
          </div>

          {/* Case Particulars Grid */}
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2.5 flex items-center gap-2">
              <FileCheck className="w-4 h-4 text-slate-600" /> 1. Particulars of Case & Investigation
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-5 rounded-2xl bg-slate-50 border border-slate-200 text-sm">
              <div>
                <span className="text-slate-500 block text-xs">Case Reference:</span>
                <span className="text-slate-900 font-bold">{caseData.case_reference_no}</span>
              </div>
              <div>
                <span className="text-slate-500 block text-xs">Crime Reference:</span>
                <span className="text-slate-900 font-bold">{caseData.fir_reference}</span>
              </div>
              <div>
                <span className="text-slate-500 block text-xs">Investigating Agency:</span>
                <span className="text-slate-800 font-medium">{caseData.investigating_agency}</span>
              </div>
              <div>
                <span className="text-slate-500 block text-xs">Jurisdiction / Police Station:</span>
                <span className="text-slate-800 font-medium">{caseData.jurisdiction_police_station}</span>
              </div>
              <div className="sm:col-span-2">
                <span className="text-slate-500 block text-xs">Session Identifier:</span>
                <span className="text-slate-700 font-mono text-xs">{caseData.session_identifier}</span>
              </div>
            </div>
          </div>

          {/* Chain of Custody & Cryptographic Hash */}
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2.5 flex items-center gap-2">
              <Lock className="w-4 h-4 text-slate-600" /> 2. Chain of Custody & Cryptographic Seal
            </h3>
            <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200 text-sm space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Media Format:</span>
                <span className="font-semibold text-slate-800">{custody.media_type}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Capture Methodology:</span>
                <span className="font-semibold text-slate-800">{custody.capture_methodology}</span>
              </div>
              <div className="flex items-start justify-between gap-4 pt-2 border-t border-slate-200">
                <span className="text-slate-500 flex items-center gap-1.5 shrink-0 text-xs font-semibold">
                  <Hash className="w-4 h-4 text-slate-400" /> SHA-256 Digest:
                </span>
                <span className="text-slate-900 break-all font-mono font-bold text-xs text-right">
                  {custody.sha256_audio_digest}
                </span>
              </div>
            </div>
          </div>

          {/* Forensic Findings & Anomaly Table */}
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2.5 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-slate-600" /> 3. Acoustic Biometrics & Neural Model Verdict
            </h3>
            <div className="overflow-hidden rounded-xl border border-slate-200">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-slate-600 text-xs uppercase font-bold border-b border-slate-200">
                  <tr>
                    <th className="p-3 font-bold">Forensic Parameter</th>
                    <th className="p-3 font-bold">Measured Value</th>
                    <th className="p-3 font-bold">Human Baseline</th>
                    <th className="p-3 font-bold">Verdict</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {(findings.acoustic_biometric_anomalies || []).map((row, idx) => (
                    <tr key={idx} className="hover:bg-slate-50/70">
                      <td className="p-3 font-medium text-slate-900">{row.metric}</td>
                      <td className="p-3 font-bold text-slate-900">{row.measured_value}</td>
                      <td className="p-3 text-slate-500 text-xs">{row.normal_human_range}</td>
                      <td className="p-3">
                        <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${
                          row.verdict.includes('CRITICAL') || row.verdict.includes('ANOMALY')
                            ? 'bg-rose-50 text-rose-700 border border-rose-200'
                            : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        }`}>
                          {row.verdict}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-4 flex flex-col sm:flex-row items-center justify-between p-4 rounded-xl bg-slate-50 border border-slate-200 text-sm gap-2">
              <div>
                <span className="text-slate-500">Threat Score:</span>{' '}
                <strong className={`text-base font-bold ${findings.composite_threat_risk >= 60 ? 'text-rose-600' : 'text-emerald-600'}`}>
                  {findings.composite_threat_risk}% ({findings.threat_classification})
                </strong>
              </div>
              <div>
                <span className="text-slate-500">Classification:</span>{' '}
                <strong className={findings.is_synthetic_cloning_detected ? 'text-rose-600 font-bold' : 'text-emerald-600 font-bold'}>
                  {findings.is_synthetic_cloning_detected ? 'CONFIRMED SYNTHETIC CLONE' : 'AUTHENTIC HUMAN SPEECH'}
                </strong>
              </div>
            </div>
          </div>

          {/* Speech Transcription & AI Threat Intelligence (if available) */}
          {dossier.speech_intelligence && (
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2.5 flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-slate-600" /> 4. Speech-to-Text Transcription & Semantic Intent Analysis
              </h3>
              <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200 text-sm space-y-4">
                {/* Transcript Box */}
                <div>
                  <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block mb-1.5">
                    Decoded Audio Transcript:
                  </span>
                  <div className="p-4 rounded-xl bg-white border border-slate-200 text-slate-900 font-medium italic leading-relaxed">
                    "{dossier.speech_intelligence.transcript}"
                  </div>
                </div>

                {/* AI Semantic Intent Assessment */}
                {dossier.speech_intelligence.ai_analysis && (
                  <div className="pt-3 border-t border-slate-200 space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <Sparkles className="w-4 h-4 text-indigo-600" />
                        <span className="font-bold text-slate-900">
                          {dossier.speech_intelligence.ai_analysis.intent_category || 'Semantic Intent Evaluated'}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        {dossier.speech_intelligence.ai_analysis.urgency_level && (
                          <span className="px-2.5 py-0.5 rounded-full text-xs font-bold uppercase bg-rose-100 text-rose-800 border border-rose-200">
                            {dossier.speech_intelligence.ai_analysis.urgency_level} Urgency
                          </span>
                        )}
                        <span className="text-xs font-mono font-bold text-slate-500">
                          Intent Risk: {dossier.speech_intelligence.ai_analysis.threat_intent_score}%
                        </span>
                      </div>
                    </div>

                    {dossier.speech_intelligence.ai_analysis.summary && (
                      <p className="text-xs text-slate-600 font-medium m-0">
                        {dossier.speech_intelligence.ai_analysis.summary}
                      </p>
                    )}

                    {dossier.speech_intelligence.ai_analysis.tactics && dossier.speech_intelligence.ai_analysis.tactics.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {dossier.speech_intelligence.ai_analysis.tactics.map((tac, idx) => (
                          <span key={idx} className="px-2 py-0.5 rounded-md bg-white border border-slate-200 text-slate-700 text-[11px] font-bold">
                            {tac}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Statutory Charges & Legal Attestation */}
          {charges.length > 0 && (
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-rose-700 mb-2 flex items-center gap-2">
                <Scale className="w-4 h-4" /> {dossier.speech_intelligence ? '5' : '4'}. Applicable Statutory Provisions (BNS 2023 & IT Act 2000)
              </h3>
              <ul className="space-y-2 p-4 rounded-xl bg-rose-50 border border-rose-200 text-sm text-rose-900">
                {charges.map((charge, i) => (
                  <li key={i} className="flex items-start gap-2.5">
                    <span className="w-2 h-2 rounded-full bg-rose-500 shrink-0 mt-2" />
                    <span className="font-medium">{charge}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Section 63 BSA 2023 Legal Attestation */}
          <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200 text-xs text-slate-600 leading-relaxed italic">
            <strong className="text-slate-900 not-italic block mb-1.5 font-bold">Statutory Declaration:</strong>
            "{dossier.statutory_attestation}"
          </div>

          {/* Signatures */}
          <div className="pt-8 border-t border-slate-200 flex flex-col sm:flex-row justify-between items-start sm:items-end text-xs text-slate-500 gap-4">
            <div>
              <p className="m-0">Certified System: <strong className="text-slate-900">Aegis Voice Sentinel</strong></p>
              <p className="mt-1 m-0">Authorized Examiner: <strong className="text-slate-900">{caseData.certifying_officer}</strong></p>
            </div>
            <div className="text-left sm:text-right">
              <div className="h-9 border-b border-slate-400 w-52 mb-1.5"></div>
              <p className="text-slate-800 font-bold m-0">Digital Signature & Hash Seal</p>
              <p className="text-slate-400 mt-0.5 m-0 font-medium">Section 63(4) Bharatiya Sakshya Adhiniyam, 2023</p>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
