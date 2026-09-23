import React from 'react';
import { ShieldCheck, ShieldAlert, AlertCircle, Lock, Zap, CheckCircle2, Volume2, Info } from 'lucide-react';

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
  const isCritical = smoothedRisk >= 75 || color === 'red';
  const isSuspicious = (smoothedRisk >= 40 && smoothedRisk < 75) || color === 'amber';
  const isIdle = status === 'IDLE_SILENCE' || (color === 'slate' && !isCritical && !isSuspicious);

  // SVG Circular Gauge calculations (176x176px gauge)
  const radius = 68;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (Math.min(100, Math.max(0, smoothedRisk)) / 100) * circumference;

  const getGaugeColor = () => {
    if (isCritical) return '#dc2626'; // rose-600
    if (isSuspicious) return '#d97706'; // amber-600
    if (isIdle) return '#94a3b8'; // slate-400
    return '#059669'; // emerald-600
  };

  const getHumanVerdict = () => {
    if (isCritical) return 'Deepfake voice detected.';
    if (isSuspicious) return 'Suspicious voice anomalies detected.';
    if (isIdle) return 'Monitoring audio stream...';
    return 'Authentic human voice verified.';
  };

  const getActionRecommendation = () => {
    if (isCritical) {
      return {
        label: 'Action Required',
        details: 'Hold operations and verify identity.',
        isAlert: true,
        type: 'critical',
      };
    }
    if (isSuspicious) {
      return {
        label: 'Notice',
        details: 'Proceed with caution.',
        isAlert: true,
        type: 'warning',
      };
    }
    if (isIdle) {
      return {
        label: 'System Ready',
        details: 'Awaiting speech input.',
        isAlert: false,
        type: 'idle',
      };
    }
    return {
      label: 'Safe to Proceed',
      details: 'No anomalies detected.',
      isAlert: false,
      type: 'safe',
    };
  };

  const getStatusBadge = () => {
    if (isCritical) {
      return {
        text: 'Synthetic Voice',
        classes: 'bg-rose-50 text-rose-800 border-rose-200 font-bold',
        icon: <ShieldAlert className="w-4 h-4 text-rose-600" aria-hidden="true" />,
      };
    }
    if (isSuspicious) {
      return {
        text: 'Suspicious Audio',
        classes: 'bg-amber-50 text-amber-800 border-amber-200 font-bold',
        icon: <AlertCircle className="w-4 h-4 text-amber-600" aria-hidden="true" />,
      };
    }
    if (isIdle) {
      return {
        text: 'Monitoring',
        classes: 'bg-slate-100 text-slate-700 border-slate-200 font-semibold',
        icon: <Volume2 className="w-4 h-4 text-slate-500" aria-hidden="true" />,
      };
    }
    return {
      text: 'Human Voice',
      classes: 'bg-emerald-50 text-emerald-800 border-emerald-200 font-bold',
      icon: <CheckCircle2 className="w-4 h-4 text-emerald-600" aria-hidden="true" />,
    };
  };

  const badge = getStatusBadge();
  const recommendation = getActionRecommendation();

  return (
    <div
      aria-labelledby="threat-assessment-title"
      className="p-6 rounded-2xl border border-slate-200 bg-white shadow-sm transition-all w-full"
    >
      {/* Card Header */}
      <div className="flex items-center justify-between pb-4 mb-5 border-b border-slate-100">
        <div className="flex items-center gap-2.5">
          {isCritical ? (
            <ShieldAlert className="w-5 h-5 text-rose-600" aria-hidden="true" />
          ) : isSuspicious ? (
            <AlertCircle className="w-5 h-5 text-amber-600" aria-hidden="true" />
          ) : isIdle ? (
            <Volume2 className="w-5 h-5 text-slate-500" aria-hidden="true" />
          ) : (
            <ShieldCheck className="w-5 h-5 text-emerald-600" aria-hidden="true" />
          )}
          <h2 id="threat-assessment-title" className="text-base font-bold text-slate-900 m-0">
            Threat Score
          </h2>
        </div>

        <div className="flex items-center gap-2">
          {isFrozen && (
            <span
              className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs font-bold"
              role="status"
            >
              <Lock className="w-3.5 h-3.5" aria-hidden="true" /> Locked
            </span>
          )}
        </div>
      </div>

      {/* Main Gauge and Status Body */}
      <div className="flex flex-col items-center gap-6">
        {/* Minimalist Circular Gauge */}
        <div
          className="relative flex items-center justify-center shrink-0"
          role="meter"
          aria-label="Synthetic Voice Threat Probability"
          aria-valuenow={Math.round(smoothedRisk)}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <svg className="w-40 h-40 transform -rotate-90" aria-hidden="true">
            {/* Background Track */}
            <circle
              cx="80"
              cy="80"
              r="58"
              stroke="#f1f5f9"
              strokeWidth="10"
              className="fill-none"
            />
            {/* Dynamic Value Arc */}
            <circle
              cx="80"
              cy="80"
              r="58"
              stroke={getGaugeColor()}
              strokeWidth="10"
              strokeDasharray={2 * Math.PI * 58}
              strokeDashoffset={2 * Math.PI * 58 - (Math.min(100, Math.max(0, smoothedRisk)) / 100) * (2 * Math.PI * 58)}
              strokeLinecap="round"
              className="fill-none transition-all duration-300 ease-out"
            />
          </svg>
          <div className="absolute flex flex-col items-center justify-center text-center">
            <span className="text-3xl font-extrabold tracking-tight text-slate-900">
              {smoothedRisk.toFixed(1)}%
            </span>
            <span className="text-xs uppercase font-bold text-slate-500 mt-1 tracking-wider">
              Threat
            </span>
          </div>
        </div>

        {/* Verdict & Description Column */}
        <div className="w-full flex flex-col items-center text-center gap-4">
          {/* Prominent Status Badge */}
          <div className="flex items-center gap-2">
            <span className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm border shadow-sm ${badge.classes}`}>
              {badge.icon}
              {badge.text}
            </span>
          </div>

          {/* High-legibility plain-English narrative */}
          <p className="text-sm text-slate-700 leading-relaxed font-medium">
            {getHumanVerdict()}
          </p>

          {/* Action Recommendation Banner */}
          <div
            className={`w-full p-4 rounded-xl border text-sm text-left flex items-start gap-3 transition-colors ${
              recommendation.type === 'critical'
                ? 'bg-rose-50 border-rose-200 text-rose-950'
                : recommendation.type === 'warning'
                ? 'bg-amber-50 border-amber-200 text-amber-950'
                : recommendation.type === 'idle'
                ? 'bg-slate-50 border-slate-200 text-slate-800'
                : 'bg-emerald-50/70 border-emerald-200 text-emerald-950'
            }`}
          >
            <div className="mt-0.5 shrink-0">
              {recommendation.type === 'critical' ? (
                <ShieldAlert className="w-5 h-5 text-rose-600" aria-hidden="true" />
              ) : recommendation.type === 'warning' ? (
                <AlertCircle className="w-5 h-5 text-amber-600" aria-hidden="true" />
              ) : recommendation.type === 'idle' ? (
                <Info className="w-5 h-5 text-slate-500" aria-hidden="true" />
              ) : (
                <CheckCircle2 className="w-5 h-5 text-emerald-600" aria-hidden="true" />
              )}
            </div>
            <div className="flex-1">
              <span className="font-bold text-slate-900 block mb-0.5">{recommendation.label}</span>
              <span className="text-slate-700">{recommendation.details}</span>
            </div>
          </div>

          {/* Metrics & Action Bar */}
          <div className="w-full flex flex-col gap-3 pt-3 border-t border-slate-100">
            <button
              onClick={onTriggerChallenge}
              className="w-full py-3 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-800 text-sm font-bold flex items-center justify-center gap-2 transition shadow-sm cursor-pointer"
              aria-label="Issue Security Challenge"
            >
              <Zap className="w-4 h-4 text-amber-500" aria-hidden="true" /> Issue Challenge
            </button>
          </div>
        </div>
      </div>

      {/* Anomalies List */}
      {anomalies && anomalies.length > 0 && (
        <div className="mt-5 pt-4 border-t border-slate-100">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2.5 flex items-center gap-1.5">
            <AlertCircle className="w-4 h-4 text-slate-400" aria-hidden="true" />
            Detected Signals
          </div>
          <div className="flex flex-wrap gap-2">
            {anomalies.map((anom, idx) => (
              <span
                key={idx}
                className="px-2.5 py-1 rounded-md bg-slate-50 border border-slate-200 text-slate-800 text-xs font-semibold shadow-sm"
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
