import React, { useState } from 'react';
import { ShieldAlert, Lock, CheckCircle, XCircle, PhoneOff, KeyRound, AlertCircle } from 'lucide-react';

export default function PreventionModal({
  isOpen,
  challenge,
  sessionId,
  onVerifyOtp,
  onQuarantine,
  onClose,
}) {
  const [inputOtp, setInputOtp] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen && !challenge) return null;

  const currentOtp = challenge?.otp_code || '849201';
  const triggerRisk = challenge?.trigger_risk || 96.4;
  const reason = challenge?.reason || 'Synthetic vocoder phase inconsistency and prosodic flattening';

  const handleVerify = async (e) => {
    e.preventDefault();
    if (!inputOtp) return;
    setIsSubmitting(true);
    setErrorMsg('');
    setSuccessMsg('');

    try {
      const res = await onVerifyOtp(inputOtp);
      if (res.success) {
        setSuccessMsg(res.message || 'OTP Verified. Call line unlocked.');
        setTimeout(() => {
          onClose();
        }, 1200);
      } else {
        setErrorMsg(res.message || 'Verification failed. Invalid OTP.');
      }
    } catch (err) {
      setErrorMsg('Error verifying OTP');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFillDemoOtp = () => {
    setInputOtp(currentOtp);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-sm p-4 animate-in fade-in duration-150">
      <div className="bg-zinc-950 border border-zinc-700 rounded-2xl max-w-lg w-full p-6 shadow-2xl relative">
        {/* Header Alert */}
        <div className="flex items-center gap-3 mb-4 pb-3 border-b border-zinc-800">
          <div className="p-2.5 bg-zinc-900 border border-zinc-700 rounded-xl text-white">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-white text-black uppercase tracking-wider">
                DEFENSE TRIGGERED
              </span>
              <span className="text-xs font-mono text-zinc-400">Threat: {triggerRisk.toFixed(1)}%</span>
            </div>
            <h3 className="text-base font-bold text-white mt-1 m-0 tracking-tight">
              SYNTHETIC VOICE INTERCEPTED
            </h3>
          </div>
        </div>

        {/* Diagnostic Banner */}
        <div className="bg-zinc-900/60 border border-zinc-800 rounded-xl p-3.5 mb-4 text-xs">
          <div className="flex items-start gap-2 text-zinc-300">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-zinc-400" />
            <div>
              <span className="font-semibold text-zinc-200">Violation: </span>
              {reason}
            </div>
          </div>
          <div className="mt-2 text-zinc-500 text-[11px] font-mono border-t border-zinc-800 pt-2 flex items-center justify-between">
            <span>Threshold: &gt; 80.0%</span>
            <span className="text-white font-semibold">STATUS: LINE LOCKED</span>
          </div>
        </div>

        {/* Action Lock Notice */}
        <div className="bg-zinc-900/40 border border-zinc-800/80 rounded-xl p-3 mb-4 text-xs">
          <div className="flex items-center gap-2 text-zinc-300 font-medium mb-1">
            <Lock className="w-3.5 h-3.5 text-zinc-400" />
            Locked In-Call Action:
          </div>
          <div className="font-mono text-zinc-400 bg-black/60 px-3 py-2 rounded-lg text-[11px] border border-zinc-900">
            Action: High-Value Financial Transfer<br />
            Status: <span className="text-white font-semibold">LOCKED</span> pending out-of-band auth.
          </div>
        </div>

        {/* Out-of-Band Challenge Form */}
        <form onSubmit={handleVerify} className="space-y-3">
          <div>
            <div className="flex items-center justify-between text-xs mb-1.5">
              <label className="text-zinc-300 font-medium flex items-center gap-1.5 text-xs font-mono">
                <KeyRound className="w-3.5 h-3.5 text-zinc-400" />
                Secondary Channel OTP:
              </label>
              <button
                type="button"
                onClick={handleFillDemoOtp}
                className="text-[10px] text-zinc-400 hover:text-white font-mono underline"
              >
                Auto-fill: {currentOtp}
              </button>
            </div>
            <input
              type="text"
              value={inputOtp}
              onChange={(e) => setInputOtp(e.target.value)}
              placeholder="000000"
              maxLength={6}
              className="w-full bg-zinc-900 border border-zinc-700 focus:border-zinc-300 text-center text-xl font-mono tracking-widest text-white rounded-xl py-2.5 focus:outline-none transition"
              autoFocus
            />
          </div>

          {errorMsg && (
            <div className="flex items-center gap-1.5 text-zinc-300 text-xs font-mono bg-zinc-900 p-2 rounded-lg border border-zinc-700">
              <XCircle className="w-4 h-4 shrink-0 text-white" />
              <span>{errorMsg}</span>
            </div>
          )}

          {successMsg && (
            <div className="flex items-center gap-1.5 text-zinc-200 text-xs font-mono bg-zinc-900 p-2 rounded-lg border border-zinc-600">
              <CheckCircle className="w-4 h-4 shrink-0 text-white" />
              <span>{successMsg}</span>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3 pt-2">
            <button
              type="submit"
              disabled={isSubmitting || !inputOtp}
              className="py-2.5 px-4 bg-white hover:bg-zinc-200 disabled:bg-zinc-800 disabled:text-zinc-600 text-black rounded-xl font-mono font-bold text-xs transition"
            >
              {isSubmitting ? 'VERIFYING...' : 'VERIFY & UNLOCK'}
            </button>

            <button
              type="button"
              onClick={onQuarantine}
              className="py-2.5 px-4 border border-zinc-800 hover:border-zinc-600 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white rounded-xl font-mono font-semibold text-xs flex items-center justify-center gap-1.5 transition"
            >
              <PhoneOff className="w-3.5 h-3.5" /> TERMINATE
            </button>
          </div>
        </form>

        {/* Dismiss Option */}
        <button
          onClick={onClose}
          className="w-full mt-3 text-center text-[11px] font-mono text-zinc-500 hover:text-zinc-300 transition"
        >
          Dismiss (Manual Override)
        </button>
      </div>
    </div>
  );
}
