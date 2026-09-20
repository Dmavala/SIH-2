import React, { useState } from 'react';
import { Mic, MicOff, Play, Square, Upload, Volume2, ShieldAlert, Sparkles, RefreshCw } from 'lucide-react';

export default function CallSimulator({
  samples,
  isMicActive,
  onToggleMic,
  isPlayingSample,
  currentSampleId,
  onPlaySample,
  onStopSample,
  onFileUpload,
  onResetBuffer,
}) {
  const [selectedSample, setSelectedSample] = useState(samples[0]?.id || 'authentic_human_english');

  const handleSelectChange = (e) => {
    const id = e.target.value;
    setSelectedSample(id);
    if (isPlayingSample) {
      onPlaySample(id);
    }
  };

  const handleToggleSamplePlay = () => {
    if (isPlayingSample) {
      onStopSample();
    } else {
      onPlaySample(selectedSample);
    }
  };

  // Quick switch between Authentic and Deepfake for instant demonstration
  const handleQuickSwitch = (targetId) => {
    setSelectedSample(targetId);
    onPlaySample(targetId);
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Volume2 className="w-5 h-5 text-cyan-400" />
          <h2 className="text-sm uppercase font-bold tracking-wider text-slate-200 m-0">
            Audio Ingestion & Call Simulator Layer
          </h2>
        </div>
        <button
          onClick={onResetBuffer}
          className="text-xs font-mono text-slate-400 hover:text-white flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 transition"
          title="Clear temporal buffer and reset threat aggregator"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Reset Buffer
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Source Option 1: Live Microphone */}
        <div className={`p-4 rounded-xl border flex flex-col justify-between ${
          isMicActive
            ? 'bg-cyan-950/40 border-cyan-500 shadow-md shadow-cyan-950/50'
            : 'bg-slate-950/60 border-slate-800'
        }`}>
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                Mode 1: Live Microphone
              </span>
              <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full ${
                isMicActive ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-slate-800 text-slate-400'
              }`}>
                {isMicActive ? 'RECORDING 16kHz' : 'MUTED'}
              </span>
            </div>
            <p className="text-xs text-slate-400 mb-3">
              Stream live audio directly from your microphone via Web Audio API worklet into the WebSocket pipeline.
            </p>
          </div>
          <button
            onClick={onToggleMic}
            className={`w-full py-2.5 px-4 rounded-xl font-medium text-xs flex items-center justify-center gap-2 transition shadow-lg ${
              isMicActive
                ? 'bg-rose-600 hover:bg-rose-500 text-white shadow-rose-900/40'
                : 'bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white shadow-cyan-950/60'
            }`}
          >
            {isMicActive ? (
              <>
                <MicOff className="w-4 h-4" /> Stop Live Mic Stream
              </>
            ) : (
              <>
                <Mic className="w-4 h-4" /> Start Live Mic Stream
              </>
            )}
          </button>
        </div>

        {/* Source Option 2: Pre-Loaded Benchmark Evaluator */}
        <div className={`p-4 rounded-xl border flex flex-col justify-between ${
          isPlayingSample
            ? 'bg-purple-950/30 border-purple-500 shadow-md shadow-purple-950/50'
            : 'bg-slate-950/60 border-slate-800'
        }`}>
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                Mode 2: Call Benchmark Feeder
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-purple-300">
                ZERO SETUP DEMO
              </span>
            </div>
            <p className="text-xs text-slate-400 mb-2">
              Stream authentic speech (Indian/English) or neural vocoder clones (HiFi-GAN/RVC) into the active call.
            </p>
            <select
              value={selectedSample}
              onChange={handleSelectChange}
              className="w-full bg-slate-900 border border-slate-700 text-slate-200 text-xs rounded-lg p-2 mb-3 font-mono focus:outline-none focus:border-cyan-500"
            >
              {samples.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.is_deepfake ? '🔴 [DEEPFAKE] ' : '🟢 [AUTHENTIC] '} {s.name}
                </option>
              ))}
            </select>
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleToggleSamplePlay}
              className={`flex-1 py-2.5 px-3 rounded-xl font-medium text-xs flex items-center justify-center gap-1.5 transition ${
                isPlayingSample
                  ? 'bg-rose-700 hover:bg-rose-600 text-white'
                  : 'bg-purple-600 hover:bg-purple-500 text-white shadow-lg shadow-purple-950/60'
              }`}
            >
              {isPlayingSample ? (
                <>
                  <Square className="w-3.5 h-3.5 fill-current" /> Stop Stream
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-current" /> Stream Sample
                </>
              )}
            </button>
          </div>
        </div>

        {/* Source Option 3: Instant Live Attack Demonstration */}
        <div className="p-4 rounded-xl border bg-slate-950/60 border-slate-800 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                Mode 3: Live Attack Switcher
              </span>
              <Sparkles className="w-4 h-4 text-amber-400" />
            </div>
            <p className="text-xs text-slate-400 mb-3">
              One-click dynamic toggle for judges: swap between authentic speech and cloned voice in under 1 second.
            </p>
          </div>

          <div className="flex flex-col gap-2">
            <button
              onClick={() => handleQuickSwitch('authentic_human_indian_accent')}
              className="w-full py-2 px-3 rounded-lg border border-emerald-700 bg-emerald-950/40 hover:bg-emerald-950/80 text-emerald-300 text-xs font-semibold flex items-center justify-between transition"
            >
              <span>🟢 Switch to Authentic Human</span>
              <span className="text-[10px] font-mono text-emerald-400">Risk &lt; 10%</span>
            </button>
            <button
              onClick={() => handleQuickSwitch('deepfake_hifi_gan')}
              className="w-full py-2 px-3 rounded-lg border border-rose-700 bg-rose-950/50 hover:bg-rose-950/90 text-rose-300 text-xs font-semibold flex items-center justify-between transition"
            >
              <span>🔴 Trigger HiFi-GAN Clone</span>
              <span className="text-[10px] font-mono text-rose-400">Risk &gt; 90%</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
