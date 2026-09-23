import React, { useEffect } from 'react';
import { Shield, CheckCircle2, AlertTriangle, Mic, Sparkles, Scale, X, Volume2, Eye, SunMedium } from 'lucide-react';

export default function UserGuideModal({ isOpen, onClose }) {
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

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby="user-guide-title"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-2xl bg-white border border-slate-200 rounded-3xl shadow-2xl overflow-hidden my-8 text-slate-800"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-7 py-5 border-b border-slate-100 bg-slate-50">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-slate-900 text-white" aria-hidden="true">
              <Shield className="w-6 h-6" />
            </div>
            <div>
              <h2 id="user-guide-title" className="text-lg font-bold text-slate-900 m-0">
                How to Use Aegis Voice Sentinel
              </h2>
              <p className="text-xs text-slate-500 m-0 mt-0.5">
                Simple, step-by-step guidance for non-technical users, bank officers, and law enforcement
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition min-w-[40px] min-h-[40px] flex items-center justify-center cursor-pointer"
            aria-label="Close user guide"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-7 space-y-6 text-sm text-slate-700 leading-relaxed max-h-[75vh] overflow-y-auto">
          {/* Quick Summary */}
          <div className="p-4 rounded-2xl bg-indigo-50/60 border border-indigo-100">
            <p className="text-slate-800 font-medium text-sm m-0">
              Aegis continuously screens calls to detect <strong>AI voice clones and deepfake impersonation scams</strong>. The system automatically inspects vocal fold tremors, acoustic phase, and breathing cadences to provide a clear, plain-English security verdict.
            </p>
          </div>

          {/* 3 Main Steps */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-indigo-600" /> 3 Steps to Screen a Call
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Step 1 */}
              <div className="p-4 rounded-2xl border border-slate-200 bg-white shadow-2xs space-y-2">
                <div className="w-8 h-8 rounded-xl bg-slate-100 border border-slate-200 font-extrabold text-slate-900 flex items-center justify-center text-sm">
                  1
                </div>
                <h4 className="font-bold text-slate-900 text-sm m-0">Connect Audio</h4>
                <p className="text-xs text-slate-600 m-0">
                  Click <strong>"Live Stream"</strong> to monitor your microphone, or use the 1-click test buttons to evaluate real vs cloned speech.
                </p>
              </div>

              {/* Step 2 */}
              <div className="p-4 rounded-2xl border border-slate-200 bg-white shadow-2xs space-y-2">
                <div className="w-8 h-8 rounded-xl bg-slate-100 border border-slate-200 font-extrabold text-slate-900 flex items-center justify-center text-sm">
                  2
                </div>
                <h4 className="font-bold text-slate-900 text-sm m-0">Read Verdict</h4>
                <p className="text-xs text-slate-600 m-0">
                  Check the circular gauge and status badge:
                  <span className="text-emerald-700 font-bold block mt-1">● Green: Authentic Human</span>
                  <span className="text-rose-700 font-bold block">● Red: Synthetic AI Clone</span>
                </p>
              </div>

              {/* Step 3 */}
              <div className="p-4 rounded-2xl border border-slate-200 bg-white shadow-2xs space-y-2">
                <div className="w-8 h-8 rounded-xl bg-slate-100 border border-slate-200 font-extrabold text-slate-900 flex items-center justify-center text-sm">
                  3
                </div>
                <h4 className="font-bold text-slate-900 text-sm m-0">Intervene & Export</h4>
                <p className="text-xs text-slate-600 m-0">
                  When risk exceeds 75%, the call automatically freezes. You can verify via secondary OTP code or generate a court-ready <strong>Section 63 BSA legal certificate</strong>.
                </p>
              </div>
            </div>
          </div>

          {/* Accessibility Features Guide */}
          <div className="space-y-3 pt-3 border-t border-slate-100">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900 flex items-center gap-2">
              <Eye className="w-4 h-4 text-indigo-600" /> Accessibility & Assistance Features
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                <strong className="text-slate-900 font-bold block mb-1">Text Scaling (A- / A+)</strong>
                Use the top navigation buttons to scale typography between Standard, Large, and Extra-Large sizes.
              </div>
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                <strong className="text-slate-900 font-bold block mb-1">High Contrast Mode</strong>
                Click the sun icon in the navigation bar to enable pure black-on-white high contrast with bold borders.
              </div>
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                <strong className="text-slate-900 font-bold block mb-1">Keyboard Navigation</strong>
                Press <kbd className="px-1.5 py-0.5 bg-white border border-slate-300 rounded font-mono text-xs">Tab</kbd> to move through all controls with high-visibility focus indicators.
              </div>
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                <strong className="text-slate-900 font-bold block mb-1">Live Screen Reader Announcements</strong>
                Threat verdict transitions and call status changes are announced automatically via ARIA live regions.
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end px-7 py-4 border-t border-slate-100 bg-slate-50">
          <button
            onClick={onClose}
            className="px-6 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-bold text-sm transition shadow-xs min-h-[42px] cursor-pointer"
          >
            Understood, Start Screening
          </button>
        </div>
      </div>
    </div>
  );
}
