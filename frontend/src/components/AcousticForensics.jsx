import React from 'react';
import { Mic, Radio, Volume2, Wind, Eye, Cpu } from 'lucide-react';

export default function AcousticForensics({ forensics, latencyMs }) {
  if (!forensics) {
    return (
      <div className="bg-zinc-950 border border-zinc-800 rounded-2xl p-6 text-center text-zinc-600 text-xs font-mono">
        Awaiting audio stream to compute acoustic forensic parameters...
      </div>
    );
  }

  const {
    pitch_mean,
    pitch_std,
    jitter_local,
    phase_dispersion,
    high_band_ratio,
    breath_pause_ratio,
    spectral_flatness,
    ambient_noise_floor_db,
    is_pristine_env,
  } = forensics;

  const isPhaseBad = phase_dispersion > 0.14;
  const isJitterFlat = pitch_mean > 60 && jitter_local < 0.0035;
  const isPitchFlat = pitch_mean > 60 && pitch_std < 5.0;
  const isPristine = is_pristine_env;
  const isHighBandAbnormal = high_band_ratio > 0.20;

  const cards = [
    {
      title: 'Phase Dispersion',
      sub: 'Harmonic Phase Coherence',
      value: phase_dispersion.toFixed(4),
      unit: 'rad²',
      benchmark: 'Human: <0.10 | Vocoder: >0.15',
      isAnomalous: isPhaseBad,
      icon: Radio,
      detail: isPhaseBad ? 'Synthetic vocoder phase perturbation detected' : 'Normal human vocal tract phase progression',
    },
    {
      title: 'Vocal Micro-Jitter',
      sub: 'F0 Period Perturbation',
      value: (jitter_local * 100).toFixed(2),
      unit: '%',
      benchmark: 'Human: 0.6% - 2.5% | TTS: <0.35%',
      isAnomalous: isJitterFlat,
      icon: Mic,
      detail: isJitterFlat ? 'Invariable jitter; vocal fold tremors absent' : 'Human vocal fold micro-tremors verified',
    },
    {
      title: 'Pitch Variance (F0)',
      sub: 'Prosodic Dynamic Range',
      value: pitch_std.toFixed(1),
      unit: 'Hz',
      benchmark: `Mean: ${pitch_mean.toFixed(0)}Hz | Std > 10Hz`,
      isAnomalous: isPitchFlat,
      icon: Volume2,
      detail: isPitchFlat ? 'Quantized pitch contour typical of TTS model' : 'Natural human conversational prosody',
    },
    {
      title: 'Acoustic Environment',
      sub: 'Background Noise & Reverb',
      value: `${ambient_noise_floor_db.toFixed(1)}`,
      unit: 'dB',
      benchmark: 'Mic: -30dB to -55dB | Vacuum: <-65dB',
      isAnomalous: isPristine,
      icon: Wind,
      detail: isPristine ? 'Synthetic digital vacuum; room reverb absent' : 'Natural room ambience & reverberation verified',
    },
    {
      title: 'Respiratory Cadence',
      sub: 'Breath & Micro-Pause Ratio',
      value: (breath_pause_ratio * 100).toFixed(1),
      unit: '%',
      benchmark: 'Human: 8% - 35% pauses',
      isAnomalous: breath_pause_ratio < 0.04,
      icon: Eye,
      detail: breath_pause_ratio < 0.04 ? 'Continuous speech lacking human respiratory pauses' : 'Natural respiratory inhalation pauses verified',
    },
    {
      title: 'Inference Latency',
      sub: 'Chunk Pipeline Speed',
      value: latencyMs > 0 ? latencyMs.toFixed(1) : '<25',
      unit: 'ms',
      benchmark: 'Real-time threshold: <150 ms',
      isAnomalous: latencyMs > 150,
      icon: Cpu,
      detail: 'Per-500ms sliding chunk analysis',
    },
  ];

  return (
    <div className="bg-zinc-950 border border-zinc-800/90 rounded-2xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xs uppercase font-mono tracking-wider text-zinc-400 m-0">
          Acoustic & Prosodic Forensics
        </h2>
        <span className="text-[10px] font-mono text-zinc-400 bg-zinc-900 border border-zinc-800 px-2.5 py-0.5 rounded-full">
          BIOMETRIC SIGNALS
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {cards.map((card, idx) => {
          const Icon = card.icon;
          return (
            <div
              key={idx}
              className={`p-3.5 rounded-xl border transition-all ${
                card.isAnomalous
                  ? 'bg-zinc-900 border-zinc-600 shadow-sm'
                  : 'bg-zinc-900/40 border-zinc-800/80 hover:border-zinc-700'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="text-zinc-400 text-xs font-medium">
                  <div>{card.title}</div>
                  <div className="text-[10px] text-zinc-500 font-mono">{card.sub}</div>
                </div>
                <div
                  className={`p-1 rounded-md ${
                    card.isAnomalous ? 'bg-zinc-800 text-white' : 'bg-zinc-900 text-zinc-500'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                </div>
              </div>

              <div className="mt-3 flex items-baseline gap-1">
                <span className="text-xl font-bold font-mono text-white">
                  {card.value}
                </span>
                <span className="text-[11px] font-mono text-zinc-500">{card.unit}</span>
              </div>

              <div className="mt-1.5 text-[10px] font-mono text-zinc-500">
                {card.benchmark}
              </div>

              <div className="mt-2 text-[10px] text-zinc-400 leading-snug border-t border-zinc-900 pt-1.5">
                {card.detail}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
