import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  Info,
  Lock,
  Ban,
  PhoneCall,
  HeartHandshake,
  AlertOctagon,
  RefreshCw,
  ShieldCheck,
} from 'lucide-react';

const generateCaptcha = () => {
  const chars = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ';
  let code = '';
  for (let i = 0; i < 4; i++) {
    code += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return code;
};

export default function SafetyAdvisoryModal({
  isOpen,
  onClose,
  threatScore = 85.0,
  modalConfig,
}) {
  const [captchaCode, setCaptchaCode] = useState(generateCaptcha);
  const [inputCaptcha, setInputCaptcha] = useState('');
  const [captchaError, setCaptchaError] = useState('');
  const [captchaSuccess, setCaptchaSuccess] = useState(false);
  const [showCaptcha, setShowCaptcha] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setCaptchaCode(generateCaptcha());
      setInputCaptcha('');
      setCaptchaError('');
      setCaptchaSuccess(false);
      setShowCaptcha(false);
    }
  }, [isOpen]);

  if (!isOpen && !modalConfig) return null;

  // Generic popup notification mode (replaces window.alert)
  if (modalConfig) {
    const {
      title = 'Notice',
      message = '',
      type = 'info',
      onConfirm,
    } = modalConfig;

    const getIcon = () => {
      switch (type) {
        case 'success':
          return <CheckCircle2 className="w-8 h-8 text-emerald-600" />;
        case 'warning':
          return <AlertTriangle className="w-8 h-8 text-amber-600" />;
        case 'error':
          return <AlertOctagon className="w-8 h-8 text-rose-600" />;
        default:
          return <Info className="w-8 h-8 text-indigo-600" />;
      }
    };

    return (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-in fade-in duration-150"
        role="dialog"
        aria-modal="true"
        aria-labelledby="generic-modal-title"
      >
        <div className="w-full max-w-md bg-white rounded-2xl border border-slate-200 shadow-2xl p-6 flex flex-col gap-5 animate-in zoom-in-95 duration-150">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-slate-100 rounded-xl shrink-0">
              {getIcon()}
            </div>
            <div className="flex-1">
              <h3 id="generic-modal-title" className="text-lg font-extrabold text-slate-900 m-0">
                {title}
              </h3>
              <p className="text-xs text-slate-600 mt-1 font-medium leading-relaxed">
                {message}
              </p>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
            <button
              onClick={() => {
                if (onConfirm) onConfirm();
                onClose();
              }}
              className="px-5 py-2.5 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-bold transition shadow-sm cursor-pointer"
            >
              Understood
            </button>
          </div>
        </div>
      </div>
    );
  }

  // --- AI VOICE DETECTED SAFETY ADVISORY POPUP ---
  const score = Number(threatScore) > 0 ? Number(threatScore) : 85.0;

  const handleRefreshCaptcha = () => {
    setCaptchaCode(generateCaptcha());
    setInputCaptcha('');
    setCaptchaError('');
  };

  const handleVerifyCaptcha = (e) => {
    e.preventDefault();
    if (!inputCaptcha) return;

    if (inputCaptcha.trim().toUpperCase() === captchaCode) {
      setCaptchaSuccess(true);
      setCaptchaError('');
      setTimeout(() => {
        onClose();
      }, 1000);
    } else {
      setCaptchaError('Incorrect verification code. Please try again.');
      setCaptchaCode(generateCaptcha());
      setInputCaptcha('');
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
      aria-labelledby="safety-modal-title"
    >
      <div className="w-full max-w-2xl bg-white rounded-2xl border border-slate-200 shadow-2xl p-6 md:p-8 flex flex-col gap-6 animate-in zoom-in-95 duration-200 max-h-[92vh] overflow-y-auto custom-scrollbar">
        
        {/* Header - No Top Right Cross Button */}
        <div className="flex items-center gap-4 pb-4 border-b border-slate-100">
          <div className="w-14 h-14 rounded-2xl bg-rose-100 text-rose-600 flex items-center justify-center shrink-0 shadow-sm">
            <ShieldAlert className="w-8 h-8" />
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-700 uppercase tracking-wider border border-rose-200">
                AI Voice Detected
              </span>
              <span className="text-xs font-bold text-slate-500">
                Threat Probability: <strong className="text-rose-600">{score.toFixed(1)}%</strong>
              </span>
            </div>
            <h2 id="safety-modal-title" className="text-xl md:text-2xl font-extrabold text-slate-900 tracking-tight m-0">
              Safety Advisory & Best Practices
            </h2>
          </div>
        </div>

        {/* Reassurance Banner: Everything is Fine */}
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center gap-3">
          <HeartHandshake className="w-5 h-5 text-emerald-600 shrink-0" />
          <div className="text-xs md:text-sm text-emerald-900 font-medium leading-relaxed">
            <strong className="font-bold text-emerald-950">Everything is under control.</strong> Testing has been automatically stopped to ensure safety. Please review the safety guidelines below.
          </div>
        </div>

        {/* The 4 Core Safety Practices */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          {/* Practice 1: Do Not Pay */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex items-start gap-3 shadow-2xs">
            <div className="p-2 bg-rose-100 text-rose-600 rounded-lg shrink-0 mt-0.5">
              <Ban className="w-4 h-4" />
            </div>
            <div>
              <strong className="text-sm font-bold text-slate-900 block mb-0.5">
                Do Not Pay or Send Money
              </strong>
              <p className="text-xs text-slate-600 m-0 font-medium leading-relaxed">
                Never transfer funds, send UPI payments, or buy gift cards under urgency from an unverified voice.
              </p>
            </div>
          </div>

          {/* Practice 2: Beware Manipulation */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex items-start gap-3 shadow-2xs">
            <div className="p-2 bg-amber-100 text-amber-700 rounded-lg shrink-0 mt-0.5">
              <AlertTriangle className="w-4 h-4" />
            </div>
            <div>
              <strong className="text-sm font-bold text-slate-900 block mb-0.5">
                Resist Urgency & Panic
              </strong>
              <p className="text-xs text-slate-600 m-0 font-medium leading-relaxed">
                Scammers create fake emergencies, arrests, or bank blocks to prevent you from thinking clearly.
              </p>
            </div>
          </div>

          {/* Practice 3: No OTP / Passwords */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex items-start gap-3 shadow-2xs">
            <div className="p-2 bg-indigo-100 text-indigo-700 rounded-lg shrink-0 mt-0.5">
              <Lock className="w-4 h-4" />
            </div>
            <div>
              <strong className="text-sm font-bold text-slate-900 block mb-0.5">
                Never Share OTPs or PINs
              </strong>
              <p className="text-xs text-slate-600 m-0 font-medium leading-relaxed">
                Legitimate police, banks, and companies will never ask for your passwords or OTP codes over any conversation.
              </p>
            </div>
          </div>

          {/* Practice 4: Independent Callback */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex items-start gap-3 shadow-2xs">
            <div className="p-2 bg-blue-100 text-blue-700 rounded-lg shrink-0 mt-0.5">
              <PhoneCall className="w-4 h-4" />
            </div>
            <div>
              <strong className="text-sm font-bold text-slate-900 block mb-0.5">
                Verify Authenticity
              </strong>
              <p className="text-xs text-slate-600 m-0 font-medium leading-relaxed">
                Contact the person or bank independently on their official, verified telephone number.
              </p>
            </div>
          </div>
        </div>

        {/* Small Captcha Verification Mode */}
        {showCaptcha ? (
          <form onSubmit={handleVerifyCaptcha} className="p-5 rounded-2xl bg-slate-50 border border-slate-200 flex flex-col gap-3 shadow-2xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-800 flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-slate-700" /> Human Security Verification
              </span>
              <span className="text-[11px] text-slate-500 font-semibold">Enter code to confirm safety</span>
            </div>

            <div className="flex flex-col sm:flex-row items-center gap-3">
              {/* Captcha Display Pill */}
              <div className="flex items-center gap-2 bg-white border border-slate-300 px-4 py-2.5 rounded-xl shadow-inner">
                <span className="font-mono text-lg font-black tracking-[0.35em] text-slate-900 select-none">
                  {captchaCode}
                </span>
                <button
                  type="button"
                  onClick={handleRefreshCaptcha}
                  className="p-1 text-slate-400 hover:text-slate-700 rounded-md transition cursor-pointer"
                  title="Generate new code"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                </button>
              </div>

              {/* Input field */}
              <input
                type="text"
                value={inputCaptcha}
                onChange={(e) => setInputCaptcha(e.target.value.toUpperCase())}
                placeholder="Enter 4 characters"
                maxLength={4}
                className="flex-1 w-full uppercase bg-white border border-slate-200 rounded-xl p-2.5 text-center text-sm font-mono font-bold tracking-widest text-slate-900 focus:outline-none focus:border-slate-400 shadow-2xs"
                autoFocus
              />

              <button
                type="submit"
                disabled={!inputCaptcha}
                className="w-full sm:w-auto py-2.5 px-5 bg-slate-900 hover:bg-slate-800 disabled:bg-slate-200 disabled:text-slate-400 text-white rounded-xl font-bold text-xs shadow-sm transition cursor-pointer"
              >
                Confirm
              </button>
            </div>

            {captchaError && (
              <div className="text-xs font-bold text-rose-700 bg-rose-50 p-2.5 rounded-xl border border-rose-200 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" /> {captchaError}
              </div>
            )}

            {captchaSuccess && (
              <div className="text-xs font-bold text-emerald-800 bg-emerald-50 p-2.5 rounded-xl border border-emerald-200 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" /> Verification Confirmed. Everything is safe.
              </div>
            )}
          </form>
        ) : null}

        {/* Clean, Consistent Action Buttons (No red button, unified styling) */}
        <div className="flex flex-col sm:flex-row items-center justify-end gap-3 pt-3 border-t border-slate-100">
          {!showCaptcha && (
            <button
              onClick={() => setShowCaptcha(true)}
              className="w-full sm:w-auto py-3 px-6 bg-slate-900 hover:bg-slate-800 text-white rounded-xl font-bold text-xs transition shadow-sm cursor-pointer flex items-center justify-center gap-2"
            >
              <ShieldCheck className="w-4 h-4 text-emerald-400" /> Verify Security (Captcha)
            </button>
          )}

          <button
            onClick={onClose}
            className="w-full sm:w-auto py-3 px-6 border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 rounded-xl font-bold text-xs transition shadow-2xs cursor-pointer"
          >
            I Am Safe (Dismiss)
          </button>
        </div>

      </div>
    </div>
  );
}
