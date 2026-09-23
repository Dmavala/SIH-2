import React, { useState } from 'react';
import {
  Mic,
  MicOff,
  RefreshCw,
  Scale,
  Play,
  Square,
  Volume2,
  Sparkles,
  PhoneCall,
  ShieldAlert,
} from 'lucide-react';

export default function CallSimulator({
  samples = [],
  isMicActive,
  onToggleMic,
  onResetBuffer,
  onGenerateDossier,
  isPlayingSample,
  currentSampleId,
  onPlaySample,
  onStopSample,
}) {
  const [selectedSampleId, setSelectedSampleId] = useState(
    samples[0]?.id || 'scam_digital_arrest'
  );

  const handleSelectChange = (e) => {
    const id = e.target.value;
    setSelectedSampleId(id);
    if (isPlayingSample && onPlaySample) {
      const s = samples.find((x) => x.id === id);
      onPlaySample(s || id);
    }
  };

  const handleToggleSample = () => {
    if (isPlayingSample && onStopSample) {
      onStopSample();
    } else if (onPlaySample) {
      const s = samples.find((x) => x.id === selectedSampleId);
      onPlaySample(s || selectedSampleId);
    }
  };

  const handleQuickPlay = (targetId) => {
    setSelectedSampleId(targetId);
    if (onPlaySample) {
      const s = samples.find((x) => x.id === targetId);
      onPlaySample(s || targetId);
    }
  };

  return (
    <section aria-labelledby="voice-testing-heading" className="flex flex-col gap-4 w-full">
      {/* Top Header / Utilities */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 id="voice-testing-heading" className="text-xl font-extrabold text-slate-900 tracking-tight m-0">
            Realtime Voice Testing & Call Simulator
          </h2>
          <p className="text-xs text-slate-500 font-medium mt-0.5">
            Test live microphone input or stream real Indian scam calls and AI voice clones into the detection engine
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onResetBuffer}
            className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-bold flex items-center gap-1.5 transition cursor-pointer shadow-2xs"
            title="Reset Audio Buffer and Unfreeze Engine"
          >
            <RefreshCw className="w-3.5 h-3.5 text-slate-500" /> Reset Engine
          </button>
          <button
            onClick={onGenerateDossier}
            className="px-3.5 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 transition cursor-pointer shadow-sm"
            title="Generate Section 63 BSA Forensic Report"
          >
            <Scale className="w-3.5 h-3.5" /> Generate Report
          </button>
        </div>
      </div>

      {/* Grid of Testing Modes */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Mode 1: Live Microphone */}
        <div
          onClick={onToggleMic}
          className={`p-4 rounded-2xl border-2 transition-all cursor-pointer flex flex-col justify-between shadow-xs ${
            isMicActive
              ? 'bg-rose-50/80 border-rose-300 shadow-rose-100'
              : 'bg-white border-slate-200 hover:border-slate-300 hover:shadow-sm'
          }`}
        >
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                Mode 1: Live Mic
              </span>
              <span
                className={`px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wider uppercase border ${
                  isMicActive
                    ? 'bg-rose-100 text-rose-800 border-rose-200 animate-pulse'
                    : 'bg-slate-100 text-slate-600 border-slate-200'
                }`}
              >
                {isMicActive ? '● Streaming' : 'Muted'}
              </span>
            </div>
            <h3 className="text-base font-extrabold text-slate-900 m-0">
              {isMicActive ? 'Microphone Active' : 'Speak into Microphone'}
            </h3>
            <p className="text-xs text-slate-500 font-medium mt-1">
              {isMicActive
                ? 'Streaming your live voice to AASIST & RawNet2 in 500ms sliding windows.'
                : 'Click to start screening your own voice for biological vocal tract jitter.'}
            </p>
          </div>

          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onToggleMic();
            }}
            className={`mt-4 w-full py-2.5 px-4 rounded-xl font-bold text-xs flex items-center justify-center gap-2 transition cursor-pointer shadow-sm ${
              isMicActive
                ? 'bg-rose-600 hover:bg-rose-700 text-white shadow-rose-200 animate-pulse'
                : 'bg-slate-900 hover:bg-slate-800 text-white'
            }`}
          >
            {isMicActive ? (
              <>
                <MicOff className="w-4 h-4" /> Stop Live Test
              </>
            ) : (
              <>
                <Mic className="w-4 h-4 text-emerald-400" /> Start Live Voice Test
              </>
            )}
          </button>
        </div>

        {/* Mode 2: Call Benchmark Feeder */}
        <div
          className={`p-4 rounded-2xl border-2 transition-all flex flex-col justify-between shadow-xs ${
            isPlayingSample
              ? 'bg-purple-50/80 border-purple-300 shadow-purple-100'
              : 'bg-white border-slate-200 hover:border-slate-300 hover:shadow-sm'
          }`}
        >
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                Mode 2: Benchmark Feeder
              </span>
              <span
                className={`px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wider uppercase border ${
                  isPlayingSample
                    ? 'bg-purple-100 text-purple-800 border-purple-200 animate-pulse'
                    : 'bg-slate-100 text-slate-600 border-slate-200'
                }`}
              >
                {isPlayingSample ? '● Feeding Track' : 'Zero Setup'}
              </span>
            </div>
            <h3 className="text-base font-extrabold text-slate-900 m-0">
              Scenario Simulator
            </h3>
            <p className="text-xs text-slate-500 font-medium mt-1 mb-2">
              Stream pre-recorded scam audio or AI voice clones into the active line:
            </p>

            <select
              value={selectedSampleId}
              onChange={handleSelectChange}
              disabled={isPlayingSample}
              className="w-full bg-slate-50 border border-slate-300 text-slate-800 text-xs rounded-xl p-2 font-medium focus:outline-none focus:border-indigo-500"
            >
              {samples && samples.length > 0 ? (
                samples.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))
              ) : (
                <>
                  <option value="scam_digital_arrest">🚨 [SCAM] Digital Arrest (Real Call)</option>
                  <option value="scam_customs_narcotics">🚨 [SCAM] Customs Narcotics Extortion</option>
                  <option value="scam_bank_kyc_fraud">🚨 [SCAM] Bank KYC Expiry Fraud</option>
                  <option value="deepfake_elevenlabs">🔴 [DEEPFAKE] ElevenLabs v3 Clone</option>
                  <option value="deepfake_hifigan">🔴 [DEEPFAKE] HiFi-GAN Neural Vocoder</option>
                  <option value="authentic_human_indian_accent">🟢 [AUTHENTIC] Indian Accent Citizen</option>
                  <option value="authentic_human_speech">🟢 [AUTHENTIC] Conversational Speech</option>
                </>
              )}
            </select>
          </div>

          <button
            type="button"
            onClick={handleToggleSample}
            className={`mt-3 w-full py-2.5 px-4 rounded-xl font-bold text-xs flex items-center justify-center gap-2 transition cursor-pointer shadow-sm ${
              isPlayingSample
                ? 'bg-rose-600 hover:bg-rose-700 text-white shadow-rose-200 animate-pulse'
                : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-indigo-200'
            }`}
          >
            {isPlayingSample ? (
              <>
                <Square className="w-3.5 h-3.5 fill-current" /> Stop Scenario
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" /> Stream Scenario
              </>
            )}
          </button>
        </div>

        {/* Mode 3: Instant Quick Attack Switcher */}
        <div className="p-4 rounded-2xl border-2 border-slate-200 bg-white shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                Mode 3: Live Attack Switcher
              </span>
              <Sparkles className="w-4 h-4 text-amber-500" />
            </div>
            <h3 className="text-base font-extrabold text-slate-900 m-0">
              One-Click Jury Demo
            </h3>
            <p className="text-xs text-slate-500 font-medium mt-1 mb-2">
              Instantly toggle between authentic human speech and high-risk AI scams:
            </p>
          </div>

          <div className="flex flex-col gap-2 mt-2">
            <button
              type="button"
              onClick={() => handleQuickPlay('authentic_human_indian_accent')}
              className={`w-full py-2 px-3 rounded-xl border text-xs font-bold flex items-center justify-between transition cursor-pointer ${
                isPlayingSample && currentSampleId === 'authentic_human_indian_accent'
                  ? 'bg-emerald-600 text-white border-emerald-600 shadow-sm'
                  : 'bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border-emerald-200'
              }`}
            >
              <span>🟢 Authentic Indian Accent</span>
              <span className="text-[10px] opacity-80">Risk &lt; 20%</span>
            </button>

            <button
              type="button"
              onClick={() => handleQuickPlay('scam_digital_arrest')}
              className={`w-full py-2 px-3 rounded-xl border text-xs font-bold flex items-center justify-between transition cursor-pointer ${
                isPlayingSample && currentSampleId === 'scam_digital_arrest'
                  ? 'bg-rose-600 text-white border-rose-600 shadow-sm animate-pulse'
                  : 'bg-rose-50 hover:bg-rose-100 text-rose-800 border-rose-200'
              }`}
            >
              <span>🚨 Digital Arrest Scam</span>
              <span className="text-[10px] opacity-80">Risk &gt; 90%</span>
            </button>

            <button
              type="button"
              onClick={() => handleQuickPlay('deepfake_elevenlabs')}
              className={`w-full py-2 px-3 rounded-xl border text-xs font-bold flex items-center justify-between transition cursor-pointer ${
                isPlayingSample && currentSampleId === 'deepfake_elevenlabs'
                  ? 'bg-purple-600 text-white border-purple-600 shadow-sm animate-pulse'
                  : 'bg-purple-50 hover:bg-purple-100 text-purple-800 border-purple-200'
              }`}
            >
              <span>🔴 ElevenLabs Voice Clone</span>
              <span className="text-[10px] opacity-80">Risk &gt; 95%</span>
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
