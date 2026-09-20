import React from 'react';
import { ShieldCheck, ShieldAlert, AlertCircle, Lock, Zap } from 'lucide-react';

export default function ThreatMeter({
  smoothedRisk,
  instantRisk,
  status,
  label,
  color,
  isFrozen,
  onTriggerChallenge,
  anomalies,
}) {
  const isCritical = smoothedRisk >= 80 || color === 'red';
  const isSuspicious = (smoothedRisk >= 40 && smoothedRisk < 80) || color === 'amber';

  // SVG Circular Gauge calculations
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (smoothedRisk / 100) * circumference;

  return (
    <div className="p-6 rounded-2xl border border-zinc-800/90 bg-zinc-950 transition-colors">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2">
          {isCritical ? (
            <ShieldAlert className="w-4 h-4 text-white" />
          ) : (
            <ShieldCheck className="w-4 h-4 text-zinc-400" />
          )}
          <h2 className="text-xs uppercase font-mono tracking-wider text-zinc-400 m-0">
            Telemetry & Biometric Risk
          </h2>
        </div>

        <div className="flex items-center gap-2">
          {isFrozen && (
            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-zinc-900 border border-zinc-700 text-white text-[11px] font-mono tracking-wider">
              <Lock className="w-3 h-3" /> CALL LOCKED
            </span>
          )}
        </div>
      </div>

      {/* Main Gauge and Status Badge */}
      <div className="flex flex-col md:flex-row items-center justify-between gap-8 py-1">
        {/* Monochromatic Circular Gauge */}
        <div className="relative flex items-center justify-center">
          <svg className="w-36 h-36 transform -rotate-90">
            {/* Background Track */}
            <circle
              cx="72"
              cy="72"
              r={radius}
              stroke="currentColor"
              strokeWidth="6"
              className="text-zinc-900 fill-none"
            />
            {/* Monochromatic Value Arc */}
            <circle
              cx="72"
              cy="72"
              r={radius}
              strokeWidth="6"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
              className="stroke-white fill-none transition-all duration-500 ease-out"
            />
          </svg>
          <div className="absolute flex flex-col items-center justify-center text-center">
            <span className="text-3xl font-bold font-mono tracking-tight text-white">
              {smoothedRisk.toFixed(1)}%
            </span>
            <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-500">
              Risk
            </span>
          </div>
        </div>

        {/* Biometric Status & Explanation */}
        <div className="flex-1 flex flex-col items-center md:items-start text-center md:text-left gap-3">
          <div className="flex items-center gap-2">
            <span
              className={`px-3 py-1.5 rounded-lg text-xs font-mono font-semibold tracking-wider uppercase border transition-all ${
                isCritical
                  ? 'bg-white text-black border-white'
                  : isSuspicious
                  ? 'bg-zinc-900 border-zinc-600 text-zinc-200'
                  : 'bg-zinc-900/60 border-zinc-800 text-zinc-400'
              }`}
            >
              {label || 'CALCULATING BIOMETRICS...'}
            </span>
          </div>

          <p className="text-xs text-zinc-400 max-w-lg leading-relaxed font-sans">
            {isCritical
              ? 'Critical synthetic signature detected: Neural vocoder phase distortion and unnatural prosodic cadence exceed safety threshold. Active defense engaged.'
              : isSuspicious
              ? 'Acoustic anomalies detected: Jitter or high-frequency spectral ratios indicate potential neural synthetic conversion. Continuous monitoring active.'
              : 'Authentic human biometrics verified: Natural vocal-fold micro-jitter, dynamic pitch variation, and physical reverberation confirmed.'}
          </p>

          {/* Quick Metrics Bar */}
          <div className="w-full flex items-center gap-6 text-xs font-mono text-zinc-500 pt-3 border-t border-zinc-900">
            <div>
              Instant: <span className="text-zinc-200 font-semibold">{instantRisk.toFixed(1)}%</span>
            </div>
            <div>
              Window Avg: <span className="text-zinc-200 font-semibold">{smoothedRisk.toFixed(1)}%</span>
            </div>
            <div className="ml-auto">
              <button
                onClick={onTriggerChallenge}
                className="px-2.5 py-1 rounded-md border border-zinc-800 bg-zinc-900 hover:border-zinc-700 hover:bg-zinc-800 text-zinc-300 text-[11px] font-mono flex items-center gap-1.5 transition"
              >
                <Zap className="w-3 h-3 text-zinc-400" /> Challenge
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Anomalies List */}
      {anomalies && anomalies.length > 0 && (
        <div className="mt-4 pt-3 border-t border-zinc-900">
          <div className="text-[11px] font-mono uppercase tracking-wider text-zinc-500 mb-2 flex items-center gap-1.5">
            <AlertCircle className="w-3.5 h-3.5 text-zinc-400" />
            Detected Anomalies ({anomalies.length}):
          </div>
          <div className="flex flex-wrap gap-1.5">
            {anomalies.map((anom, idx) => (
              <span
                key={idx}
                className="px-2.5 py-1 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-300 text-xs font-mono"
              >
                {anom}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
