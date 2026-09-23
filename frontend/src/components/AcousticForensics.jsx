import React from 'react';
import { Mic, Radio, Volume2, Wind, Eye, Cpu, CheckCircle2, AlertTriangle } from 'lucide-react';

export default function AcousticForensics({ forensics, latencyMs }) {
  if (!forensics) {
    return (
      <section aria-labelledby="forensics-heading" className="bg-white border border-slate-200 rounded-2xl p-8 text-center text-slate-500 text-sm shadow-sm">
        <h2 id="forensics-heading" className="sr-only">Acoustic Forensic Indicators</h2>
        <div className="flex flex-col items-center justify-center gap-3 py-6">
          <Volume2 className="w-8 h-8 text-slate-400 animate-pulse" aria-hidden="true" />
          <p className="m-0 font-medium text-slate-700">Awaiting audio stream to compute acoustic forensic parameters...</p>
          <span className="text-xs text-slate-500">Play an audio sample or start the microphone to stream live biometric measurements</span>
        </div>
      </section>
    );
  }

  const {
    pitch_mean = 0,
    pitch_std = 0,
    jitter_local = 0,
    phase_dispersion = 0,
    breath_pause_ratio = 0,
    ambient_noise_floor_db = -90,
    is_pristine_env = false,
  } = forensics;

  const isPhaseBad = phase_dispersion > 0.14;
  const isJitterFlat = pitch_mean > 60 && jitter_local < 0.0035;
  const isPitchFlat = pitch_mean > 60 && pitch_std < 5.0;
  const isPristine = is_pristine_env;

  const cards = [
    {
      title: 'Phase Dispersion',
      sub: 'Harmonic Coherence',
      value: phase_dispersion.toFixed(4),
      unit: 'rad²',
      plainExplanation: 'Evaluates whether sound wave harmonics align organically or show neural vocoder phase tearing.',
      benchmark: 'Organic: <0.10 | Synthetic: >0.14',
      isAnomalous: isPhaseBad,
      icon: Radio,
    },
    {
      title: 'Vocal Micro-Jitter',
      sub: 'Pitch Cycle Variation',
      value: (jitter_local * 100).toFixed(2),
      unit: '%',
      plainExplanation: 'Human vocal cords naturally vibrate with micro-variations; cloned speech is unnaturally steady.',
      benchmark: 'Organic: 0.6% - 2.5% | AI TTS: <0.35%',
      isAnomalous: isJitterFlat,
      icon: Mic,
    },
    {
      title: 'Pitch Variance (F0)',
      sub: 'Prosodic Cadence',
      value: pitch_std.toFixed(1),
      unit: 'Hz',
      plainExplanation: 'Measures natural emotional inflection and melody across syllables.',
      benchmark: `Mean: ${pitch_mean.toFixed(0)}Hz | Std > 10Hz`,
      isAnomalous: isPitchFlat,
      icon: Volume2,
    },
    {
      title: 'Ambient Noise Floor',
      sub: 'Room Acoustics',
      value: `${ambient_noise_floor_db.toFixed(1)}`,
      unit: 'dB',
      plainExplanation: 'Real speech carries environmental reverberation; AI speech often emerges from sterile digital silence.',
      benchmark: 'Room Ambience: -30 to -55 dB | Clean Studio: <-65 dB',
      isAnomalous: isPristine,
      icon: Wind,
    },
    {
      title: 'Breath Pause Cadence',
      sub: 'Respiratory Cadence',
      value: (breath_pause_ratio * 100).toFixed(1),
      unit: '%',
      plainExplanation: 'Verifies normal human breathing pauses between sentences and clauses.',
      benchmark: 'Human Cadence: 8% - 35%',
      isAnomalous: breath_pause_ratio < 0.04,
      icon: Eye,
    },
    {
      title: 'Inference Latency',
      sub: 'Detection Speed',
      value: latencyMs > 0 ? latencyMs.toFixed(1) : '<25',
      unit: 'ms',
      plainExplanation: 'Round-trip neural inference duration per audio analysis hop window.',
      benchmark: 'Real-time requirement: < 100 ms',
      isAnomalous: latencyMs > 150,
      icon: Cpu,
    },
  ];

  return (
    <div aria-labelledby="forensics-heading" className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm transition-all w-full">
      <div className="flex flex-col gap-1 mb-5 pb-4 border-b border-slate-100">
        <h2 id="forensics-heading" className="text-base font-bold text-slate-900 m-0">
          Acoustic Forensics
        </h2>
        <p className="text-xs text-slate-500 m-0 font-medium">
          Biomechanical vocal tract analysis
        </p>
      </div>

      <div className="flex flex-col gap-3">
        {cards.map((item, idx) => {
          const Icon = item.icon;
          return (
            <div
              key={idx}
              className={`p-3 rounded-xl border flex items-center justify-between transition-all ${
                item.isAnomalous
                  ? 'bg-rose-50/80 border-rose-200'
                  : 'bg-slate-50/80 border-slate-200'
              }`}
            >
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${item.isAnomalous ? 'bg-rose-100 text-rose-600' : 'bg-slate-200 text-slate-600'}`}>
                  <Icon className="w-4 h-4" aria-hidden="true" />
                </div>
                <div className="flex flex-col">
                  <span className="text-sm font-bold text-slate-900">{item.title}</span>
                  <span className="text-xs font-semibold text-slate-500">{item.benchmark}</span>
                </div>
              </div>
              <div className="flex flex-col items-end">
                <span className={`text-base font-extrabold ${item.isAnomalous ? 'text-rose-700' : 'text-slate-900'}`}>
                  {item.value} <span className="text-xs text-slate-500 font-semibold">{item.unit}</span>
                </span>
                {item.isAnomalous ? (
                  <span className="text-[10px] uppercase font-bold text-rose-600 tracking-wider">Anomaly</span>
                ) : (
                  <span className="text-[10px] uppercase font-bold text-emerald-600 tracking-wider">Normal</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
