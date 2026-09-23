/**
 * useDossier — LEA forensic dossier generation (Section 63 BSA 2023).
 * Extracted from App.jsx; removes duplicated fetch/payload code.
 */

import { useCallback } from 'react';
import { apiUrl } from '../config';

export default function useDossier({ sessionId, smoothedRisk, instantRisk, status,
                                     forensics, anomalies, telephonyMode, showPopup }) {
  const buildPayload = useCallback((caseMetadata) => ({
    session_id: sessionId || 'SES-DEMO-I4C',
    threat_score: smoothedRisk,
    status,
    forensics: forensics || {
      pitch_mean: 180.5,
      pitch_std: 42.1,
      jitter_local: 0.0035,
      shimmer_local: 0.125,
      phase_dispersion: 0.082,
      ambient_noise_floor_db: -74.2,
    },
    anomalies: anomalies.length > 0
      ? anomalies
      : ['Neural Vocoder Phase Inconsistency', 'Pristine Digital Background Vacuum'],
    model_consensus: {
      aasist_prob: smoothedRisk / 100.0,
      rawnet_prob: instantRisk / 100.0,
      telephony_tested: telephonyMode,
    },
    case_metadata: caseMetadata,
  }), [sessionId, smoothedRisk, instantRisk, status, forensics, anomalies, telephonyMode]);

  const postDossier = useCallback(async (payload, onErrorTitle) => {
    try {
      const res = await fetch(apiUrl('/api/generate-dossier'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      return await res.json();
    } catch (err) {
      console.error('Error generating forensic dossier:', err);
      showPopup({
        title: onErrorTitle || 'Report Notice',
        message: 'Could not generate forensic dossier. Please ensure the backend server is running.',
        type: 'error',
      });
      return null;
    }
  }, [showPopup]);

  const generateDossier = useCallback((setDossierData, setIsDossierOpen) =>
    postDossier(buildPayload({
      case_no: `NCRP/CYBER/${new Date().getFullYear()}/SIH-${Math.floor(100000 + Math.random() * 900000)}`,
      fir_ref: smoothedRisk >= 60
        ? 'FIR REGISTERED UNDER SEC 66D IT ACT & SEC 318 BNS'
        : 'CLEARED / AUTHENTIC CITIZEN TRAFFIC',
      police_station: 'Cyber Crime Police Station, Special Cell (I4C Node)',
      officer: 'Inspector (Digital Forensics & Audio Anti-Spoofing)',
    })).then((cert) => {
      if (cert) { setDossierData(cert); setIsDossierOpen(true); }
    }), [buildPayload, postDossier, smoothedRisk]);

  const generateDossierWithCustomMeta = useCallback((customMeta, setDossierData, setIsDossierOpen) =>
    postDossier(buildPayload(customMeta), 'Report Notice').then((cert) => {
      if (cert) { setDossierData(cert); setIsDossierOpen(true); }
    }), [buildPayload, postDossier]);

  const generateDossierFromFile = useCallback((filePayload, setDossierData, setIsDossierOpen) =>
    postDossier(filePayload, 'Report Notice').then((cert) => {
      if (cert) { setDossierData(cert); setIsDossierOpen(true); }
    }), [postDossier]);

  return { generateDossier, generateDossierWithCustomMeta, generateDossierFromFile };
}
