import React from 'react';
import { Mic, MicOff, RefreshCw, Scale, Radio, Activity } from 'lucide-react';

export default function CallSimulator({
  isMicActive,
  onToggleMic,
  onResetBuffer,
  onGenerateDossier,
}) {
  return (
    <section aria-labelledby="voice-testing-heading" className="flex flex-col gap-5 w-full">
      {/* Top Header / Utilities */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 id="voice-testing-heading" className="text-xl font-extrabold text-slate-900 tracking-tight m-0">
            Realtime Voice Testing
          </h2>
          <p className="text-xs text-slate-500 font-medium mt-1">
            Speak into your microphone to screen live voice streams for AI cloning & neural deepfakes
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <button
            onClick={onResetBuffer}
            className="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-bold flex items-center gap-2 transition cursor-pointer shadow-2xs"
            title="Reset Audio Buffer"
          >
            <RefreshCw className="w-3.5 h-3.5 text-slate-500" /> Reset Stream
          </button>
          <button
            onClick={onGenerateDossier}
            className="px-3.5 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-bold flex items-center gap-2 transition cursor-pointer shadow-sm"
            title="Generate Section 63 BSA Forensic Report"
          >
            <Scale className="w-3.5 h-3.5" /> Generate Report
          </button>
        </div>
      </div>

      {/* BIG LIVE TEST SMOOTH UI SPEAKER CARD */}
      <div
        onClick={onToggleMic}
        className={`p-6 rounded-2xl border-2 transition-all cursor-pointer flex flex-col md:flex-row items-center justify-between gap-6 shadow-sm ${
          isMicActive
            ? 'bg-rose-50/70 border-rose-300 shadow-rose-100'
            : 'bg-white border-slate-200 hover:border-slate-300 hover:shadow-md'
        }`}
      >
        {/* Left Side: Massive Smooth Speaker / Mic Button */}
        <div className="flex items-center gap-6">
          <div
            className={`w-20 h-20 rounded-2xl flex items-center justify-center shrink-0 transition-all ${
              isMicActive
                ? 'bg-rose-500 text-white shadow-[0_0_30px_rgba(244,63,94,0.45)] animate-pulse'
                : 'bg-slate-100 text-slate-500 group-hover:bg-slate-200'
            }`}
          >
            {isMicActive ? <MicOff className="w-9 h-9" /> : <Mic className="w-9 h-9" />}
          </div>

          <div className="flex flex-col">
            <div className="flex items-center gap-2.5 mb-1">
              <span
                className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold tracking-wider uppercase border ${
                  isMicActive
                    ? 'bg-rose-100 text-rose-800 border-rose-200 animate-pulse'
                    : 'bg-slate-100 text-slate-600 border-slate-200'
                }`}
              >
                {isMicActive ? '● Recording Active' : 'Ready'}
              </span>
              <span className="text-xs text-slate-400 font-semibold">16 kHz PCM Mono</span>
            </div>
            <h3 className="text-lg font-extrabold text-slate-900 m-0">
              {isMicActive ? 'Live Voice Stream Connected' : 'Live Microphone Input'}
            </h3>
            <p className="text-xs text-slate-500 font-medium mt-0.5 m-0">
              {isMicActive
                ? 'Streaming audio continuously to neural anti-spoofing engine. Click to stop.'
                : 'Click to start microphone and speak normally to test your voice.'}
            </p>
          </div>
        </div>

        {/* Right Side: Primary Action Button & Audio Pipeline Spec Badges */}
        <div className="flex flex-wrap items-center gap-3 shrink-0 self-center">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onToggleMic();
            }}
            className={`px-5 py-3 rounded-xl font-bold text-xs flex items-center gap-2 transition cursor-pointer shadow-sm ${
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

          <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-center min-w-[85px]">
            <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">Sample Rate</span>
            <span className="text-xs font-bold text-slate-800 font-mono">16,000 Hz</span>
          </div>
          <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-center min-w-[85px]">
            <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">Hop Window</span>
            <span className="text-xs font-bold text-slate-800 font-mono">500 ms</span>
          </div>
          <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-center min-w-[85px]">
            <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">Inference</span>
            <span className="text-xs font-bold text-emerald-600 font-mono">&lt; 25 ms</span>
          </div>
        </div>
      </div>
    </section>
  );
}
