import React, { useState, useEffect, useCallback } from 'react';
import Navbar from './components/Navbar';
import ThreatMeter from './components/ThreatMeter';
import SpectralWaterfall from './components/SpectralWaterfall';
import AcousticForensics from './components/AcousticForensics';
import CallSimulator from './components/CallSimulator';
import ForensicDossierModal from './components/ForensicDossierModal';
import FileAnalyzer from './components/FileAnalyzer';
import CaseAuditPortal from './components/CaseAuditPortal';
import UserGuideModal from './components/UserGuideModal';
import SafetyAdvisoryModal from './components/SafetyAdvisoryModal';
import { Activity } from 'lucide-react';
import { apiUrl } from './config';
import useAegisStream from './hooks/useAegisStream';
import useDossier from './hooks/useDossier';

export default function App() {
  // Navigation State
  const [activeTab, setActiveTab] = useState('sentinel'); // 'sentinel' | 'analyzer' | 'audit' | 'engine'

  // Audit log state
  const [auditEvents, setAuditEvents] = useState([]);

  // Modals
  const [isSafetyModalOpen, setIsSafetyModalOpen] = useState(false);
  const [genericModalConfig, setGenericModalConfig] = useState(null);
  const [isGuideOpen, setIsGuideOpen] = useState(false);

  // LEA Forensic Dossier State (BSA 2023)
  const [isDossierOpen, setIsDossierOpen] = useState(false);
  const [dossierData, setDossierData] = useState(null);

  // Accessibility & Guided UI State
  const [fontSize, setFontSize] = useState('md'); // 'sm' | 'md' | 'lg' | 'xl'
  const [isHighContrast, setIsHighContrast] = useState(false);
  const [isReducedMotion, setIsReducedMotion] = useState(false);
  const [isSoundAlerts, setIsSoundAlerts] = useState(false);
  const [isDyslexicFont, setIsDyslexicFont] = useState(false);
  const [srAnnouncement, setSrAnnouncement] = useState('Aegis Voice Sentinel loaded and ready.');

  // Samples state for benchmark call simulator
  const [samples, setSamples] = useState([]);

  // Settings & Controls
  const [activeModel, setActiveModel] = useState('AASIST');

  // Universal Modal Popup Helper (Replaces window.alert across the site)
  const showPopup = useCallback(({ title, message, type = 'info', onConfirm }) => {
    setGenericModalConfig({ title, message, type, onConfirm });
  }, []);

  const [threatModalScore, setThreatModalScore] = useState(0);

  // ---------------------------------------------------------------
  // Real-time streaming (WebSocket + telemetry + mic) via hook
  // ---------------------------------------------------------------
  const handleThreatDetected = useCallback((data) => {
    const detected = Number(data?.smoothed_risk || data?.instant_risk || 85.0);
    setThreatModalScore(detected);
    setIsSafetyModalOpen(true);
    setSrAnnouncement('Warning: synthetic voice detected on this line. Call frozen pending verification.');
  }, []);

  const handleMicError = useCallback(() => {
    showPopup({
      title: 'Microphone Permission Needed',
      message: 'Microphone access was denied or is not supported. Please allow microphone permissions in your browser to analyze live speech.',
      type: 'warning',
    });
  }, [showPopup]);

  const stream = useAegisStream({
    onThreatDetected: handleThreatDetected,
    onMicError: handleMicError,
  });
  const {
    isConnected, sessionId, smoothedRisk, instantRisk, status, label, color,
    anomalies, forensics, latencyMs, waveform, spectral,
    isFrozen, activeChallenge, setActiveChallenge,
    isMicActive, stopMic, resumeAfterThreat,
    isPlayingSample, currentSampleId, playSample, stopSample,
    telephonyMode, handleToggleTelephony, handleResetBuffer,
  } = stream;

  // ---------------------------------------------------------------
  // Dossier generation via hook
  // ---------------------------------------------------------------
  const dossier = useDossier({
    sessionId, smoothedRisk, instantRisk, status,
    forensics, anomalies, telephonyMode, showPopup,
  });

  // 1. Fetch Health, Samples, and Audit Log on mount
  const fetchAuditLog = useCallback(() => {
    fetch(apiUrl('/api/audit-log'))
      .then((res) => res.json())
      .then((data) => setAuditEvents(Array.isArray(data) ? data : []))
      .catch((err) => console.error('Error fetching audit log:', err));
  }, []);

  useEffect(() => {
    fetch(apiUrl('/api/health'))
      .then((res) => res.json())
      .then((data) => {
        if (data.active_model) setActiveModel(data.active_model);
      })
      .catch((err) => console.error('Error fetching health:', err));

    fetch(apiUrl('/api/samples'))
      .then((res) => res.json())
      .then((data) => setSamples(Array.isArray(data) ? data : []))
      .catch((err) => console.error('Error fetching samples:', err));

    fetchAuditLog();
  }, [fetchAuditLog]);

  // 4. Controls & Prevention actions
  const handleManualTriggerChallenge = async () => {
    try {
      const res = await fetch(apiUrl('/api/trigger-challenge'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId || 'SES-DEMO',
          trigger_risk: smoothedRisk,
          reason: anomalies[0] || 'Operator triggered manual forensic challenge',
        }),
      });
      const data = await res.json();
      setActiveChallenge(data);
      setIsSafetyModalOpen(true);
      fetchAuditLog();
    } catch (err) {
      console.error('Error triggering challenge:', err);
    }
  };

  const handleVerifyOtp = async (otpCode) => {
    const res = await fetch(apiUrl('/api/verify-otp'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId || activeChallenge?.session_id,
        otp_code: otpCode,
      }),
    });
    const result = await res.json();
    fetchAuditLog();
    return result;
  };

  const handleQuarantine = async () => {
    stopMic();
    await fetch(apiUrl('/api/quarantine'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId || activeChallenge?.session_id,
        reason: 'Operator terminated and quarantined voice line due to confirmed deepfake attack',
      }),
    });
    setIsSafetyModalOpen(false);
    fetchAuditLog();
    showPopup({
      title: 'Call Quarantined',
      message: 'The suspicious voice line has been terminated and quarantined. An incident log has been registered.',
      type: 'success',
    });
  };

  const handleGenerateDossier = () =>
    dossier.generateDossier(setDossierData, setIsDossierOpen);
  const handleGenerateDossierWithCustomMeta = (meta) =>
    dossier.generateDossierWithCustomMeta(meta, setDossierData, setIsDossierOpen);
  const handleGenerateDossierFromFile = (payload) =>
    dossier.generateDossierFromFile(payload, setDossierData, setIsDossierOpen);

  // Reset closes the alert modal too (modal state lives at this level)
  const handleFullReset = () => {
    if (stopSample) stopSample();
    handleResetBuffer();
    setIsSafetyModalOpen(false);
    setGenericModalConfig(null);
    setActiveChallenge(null);
    setThreatModalScore(0);
  };

  // Closing the threat advisory RESUMES realtime analysis
  const handleSafetyModalClose = useCallback(() => {
    if (stopSample) stopSample();
    setIsSafetyModalOpen(false);
    setThreatModalScore(0);
    setActiveChallenge(null);
    resumeAfterThreat();
  }, [resumeAfterThreat, stopSample]);

  // Toggle mic closes any open safety alerts and begins fresh recording session
  const handleToggleMic = useCallback(() => {
    if (stopSample) stopSample();
    setIsSafetyModalOpen(false);
    setGenericModalConfig(null);
    setThreatModalScore(0);
    stream.handleToggleMic();
  }, [stream, stopSample]);

  return (
    <div className={`h-screen w-screen bg-slate-50 text-slate-900 flex flex-col overflow-hidden font-sans antialiased font-scale-${fontSize} ${isHighContrast ? 'high-contrast' : ''} ${isReducedMotion ? 'reduce-motion' : ''} ${isDyslexicFont ? 'dyslexia-font' : ''}`}>
      {/* Screen Reader Live Announcements */}
      <div role="status" aria-live="polite" className="sr-only">
        {srAnnouncement}
      </div>

      {/* Accessible Multi-Tab Navigation Bar */}
      <Navbar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        activeModel={activeModel}
        isConnected={isConnected}
        isMicActive={isMicActive}
        onToggleMic={handleToggleMic}
        fontSize={fontSize}
        onChangeFontSize={setFontSize}
        isHighContrast={isHighContrast}
        onToggleHighContrast={() => setIsHighContrast((prev) => !prev)}
        isReducedMotion={isReducedMotion}
        onToggleReducedMotion={() => setIsReducedMotion((prev) => !prev)}
        isSoundAlerts={isSoundAlerts}
        onToggleSoundAlerts={() => setIsSoundAlerts((prev) => !prev)}
        isDyslexicFont={isDyslexicFont}
        onToggleDyslexicFont={() => setIsDyslexicFont((prev) => !prev)}
        onOpenHelpGuide={() => setIsGuideOpen(true)}
      />

      {/* Main Content Area - NO SCROLL, FLEX LAYOUT */}
      <main id="main-content" role="main" tabIndex="-1" className="flex-1 flex flex-col w-full h-full overflow-hidden">

        {/* Tab 1: Live Call Sentinel */}
        <div
          className={`flex-1 flex-row overflow-hidden p-6 gap-6 w-full h-full ${
            activeTab === 'sentinel' ? 'flex' : 'hidden'
          }`}
          role="region"
          aria-label="Live Call Screening Workspace"
        >
          {/* Left Column: Realtime Analysis, Score UI, Status */}
          <div className="w-[420px] flex-shrink-0 flex flex-col gap-6 overflow-y-auto pr-2 pb-6 custom-scrollbar">
            <ThreatMeter
              smoothedRisk={smoothedRisk}
              instantRisk={instantRisk}
              status={status}
              label={label}
              color={color}
              isFrozen={isFrozen}
              anomalies={anomalies}
              onTriggerChallenge={handleManualTriggerChallenge}
            />
            <AcousticForensics forensics={forensics} latencyMs={latencyMs} />
          </div>

          {/* Center Column: Big Live Speaker Voice Tester & Realtime Waveform Viewer */}
          <div className="flex-1 flex flex-col bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden p-6 gap-5">
            {/* Top: Big Live Speaker & Voice Testing Control */}
            <CallSimulator
              samples={samples}
              isMicActive={isMicActive}
              onToggleMic={handleToggleMic}
              onResetBuffer={handleFullReset}
              onGenerateDossier={handleGenerateDossier}
              isPlayingSample={isPlayingSample}
              currentSampleId={currentSampleId}
              onPlaySample={playSample}
              onStopSample={stopSample}
            />

            {/* Bottom: Expansive Realtime Waveform & Waterfall Viewer */}
            <div className="flex-1 flex flex-col min-h-0 bg-slate-50/60 rounded-2xl border border-slate-200 p-4 shadow-xs overflow-hidden">
              <div className="pb-3 mb-2 border-b border-slate-200 flex items-center justify-between">
                <span className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
                  <Activity className="w-4 h-4 text-indigo-600" /> Realtime Audio Decoder & Spectral Analyzer
                </span>
                <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold ${
                  isMicActive
                    ? 'bg-emerald-100 text-emerald-800 border border-emerald-300 animate-pulse'
                    : 'bg-white text-slate-500 border border-slate-200'
                }`}>
                  {isMicActive ? '● LIVE INPUT ACTIVE' : 'AWAITING MIC'}
                </span>
              </div>
              <div className="flex-1 relative w-full h-full min-h-0">
                <SpectralWaterfall
                  waveform={waveform}
                  spectral={spectral}
                  isSynthetic={smoothedRisk >= 75 || color === 'red'}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Tab 2: File Forensic Investigator */}
        <div
          className={`flex-1 overflow-y-auto p-6 custom-scrollbar ${
            activeTab === 'analyzer' ? 'block' : 'hidden'
          }`}
          role="region"
          aria-label="File Forensic Investigator Workspace"
        >
          <FileAnalyzer onGenerateDossierForFile={handleGenerateDossierFromFile} />
        </div>

        {/* Tab 3: I4C Case Dossier & Reports */}
        <div
          className={`flex-1 overflow-y-auto p-6 custom-scrollbar ${
            activeTab === 'audit' ? 'block' : 'hidden'
          }`}
          role="region"
          aria-label="Case Audit & Dossier Reports Workspace"
        >
          <CaseAuditPortal
            events={auditEvents}
            onRefresh={fetchAuditLog}
            onOpenDossierWithCustomMeta={handleGenerateDossierWithCustomMeta}
            currentRisk={smoothedRisk}
            currentStatus={status}
            forensics={forensics}
            anomalies={anomalies}
          />
        </div>

      </main>


      {/* Section 63 BSA 2023 Forensic Evidence Certificate Modal */}
      <ForensicDossierModal
        isOpen={isDossierOpen}
        dossier={dossierData}
        onClose={() => setIsDossierOpen(false)}
      />

      {/* Beginner User Guide & Assistance Modal */}
      <UserGuideModal
        isOpen={isGuideOpen}
        onClose={() => setIsGuideOpen(false)}
      />

      {/* AI Voice Safety Advisory & Alert Modal (Best Practices & Alert Replacement) */}
      <SafetyAdvisoryModal
        isOpen={isSafetyModalOpen || !!genericModalConfig}
        onClose={genericModalConfig ? handleFullReset : handleSafetyModalClose}
        threatScore={threatModalScore || smoothedRisk}
        modalConfig={genericModalConfig}
      />
    </div>
  );
}
