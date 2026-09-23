import React from 'react';
import { Shield, Radio, FileAudio, Scale, Eye, HelpCircle, SunMedium, Type, Volume2, VolumeX, BookOpen } from 'lucide-react';

export default function Navbar({
  activeTab = 'sentinel',
  onTabChange,
  activeModel = 'AASIST',
  isConnected,
  isMicActive,
  onToggleMic,
  fontSize = 'md',
  onChangeFontSize,
  isHighContrast = false,
  onToggleHighContrast,
  isReducedMotion = false,
  onToggleReducedMotion,
  isSoundAlerts = false,
  onToggleSoundAlerts,
  isDyslexicFont = false,
  onToggleDyslexicFont,
  onOpenHelpGuide,
}) {
  const tabs = [
    { id: 'sentinel', label: 'Live', icon: Radio },
    { id: 'analyzer', label: 'File Analysis', icon: FileAudio },
    { id: 'audit', label: 'Reports', icon: Scale },
  ];

  const handleToggleFont = () => {
    if (fontSize === 'md') onChangeFontSize('lg');
    else if (fontSize === 'lg') onChangeFontSize('xl');
    else onChangeFontSize('md');
  };

  return (
    <>
      <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:p-4 focus:bg-white focus:text-slate-900 focus:z-50">
        Skip to main content
      </a>

      <header role="banner" className="bg-white border-b border-slate-200 sticky top-0 z-40 px-6 py-4 shadow-sm">
        <div className="w-full flex items-center justify-between">
          
          {/* LEFT: Brand Logo + Name */}
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-slate-900 text-white rounded-xl" aria-hidden="true">
              <Shield className="w-5 h-5" />
            </div>
            <div className="flex flex-col">
              <span className="text-lg font-extrabold tracking-tight text-slate-900 leading-none">
                AEGIS
              </span>
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-widest mt-1">
                Sentinel
              </span>
            </div>
          </div>

          {/* MIDDLE: Dock Style Navbar */}
          <nav aria-label="Main Navigation" className="absolute left-1/2 -translate-x-1/2 flex items-center bg-slate-100 p-1.5 rounded-2xl border border-slate-200 shadow-inner">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => onTabChange && onTabChange(tab.id)}
                  aria-current={isActive ? 'page' : undefined}
                  className={`flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-bold transition-all cursor-pointer ${
                    isActive
                      ? 'bg-white text-slate-900 shadow-sm border border-slate-200'
                      : 'text-slate-500 hover:text-slate-900 hover:bg-slate-200/50'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-indigo-600' : 'text-slate-400'}`} aria-hidden="true" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </nav>

          {/* RIGHT: Accessibility & Controls */}
          <div className="flex items-center gap-2">
            <div className="flex items-center bg-slate-50 border border-slate-200 rounded-xl p-1" role="group" aria-label="Accessibility controls">
              <button
                onClick={handleToggleFont}
                className="p-2 text-slate-600 hover:bg-white hover:text-slate-900 rounded-lg transition-colors cursor-pointer flex items-center justify-center"
                title={`Text Size (${fontSize.toUpperCase()})`}
                aria-label={`Toggle text size, currently ${fontSize}`}
              >
                <Type className="w-4 h-4" aria-hidden="true" />
              </button>
              
              <div className="w-px h-5 bg-slate-200 mx-0.5" aria-hidden="true" />

              <button
                onClick={onToggleHighContrast}
                className={`p-2 rounded-lg transition-colors cursor-pointer flex items-center justify-center ${
                  isHighContrast ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-white hover:text-slate-900'
                }`}
                title="Toggle High Contrast"
                aria-label="Toggle high contrast"
                aria-pressed={isHighContrast}
              >
                <SunMedium className="w-4 h-4" aria-hidden="true" />
              </button>

              <div className="w-px h-5 bg-slate-200 mx-0.5" aria-hidden="true" />

              <button
                onClick={onToggleReducedMotion}
                className={`p-2 rounded-lg transition-colors cursor-pointer flex items-center justify-center ${
                  isReducedMotion ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-white hover:text-slate-900'
                }`}
                title="Toggle Reduced Motion"
                aria-label="Toggle reduced motion"
                aria-pressed={isReducedMotion}
              >
                <Eye className="w-4 h-4" aria-hidden="true" />
              </button>

              <div className="w-px h-5 bg-slate-200 mx-0.5" aria-hidden="true" />

              <button
                onClick={onToggleSoundAlerts}
                className={`p-2 rounded-lg transition-colors cursor-pointer flex items-center justify-center ${
                  isSoundAlerts ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-white hover:text-slate-900'
                }`}
                title="Audio Cues / Screen Reader Alerts"
                aria-label="Toggle audio cue alerts"
                aria-pressed={isSoundAlerts}
              >
                {isSoundAlerts ? <Volume2 className="w-4 h-4" aria-hidden="true" /> : <VolumeX className="w-4 h-4" aria-hidden="true" />}
              </button>

              <div className="w-px h-5 bg-slate-200 mx-0.5" aria-hidden="true" />

              <button
                onClick={onToggleDyslexicFont}
                className={`p-2 rounded-lg transition-colors cursor-pointer flex items-center justify-center ${
                  isDyslexicFont ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-white hover:text-slate-900'
                }`}
                title="Toggle High-Legibility Font"
                aria-label="Toggle high legibility font"
                aria-pressed={isDyslexicFont}
              >
                <BookOpen className="w-4 h-4" aria-hidden="true" />
              </button>
            </div>

            <button
              onClick={onOpenHelpGuide}
              className="ml-1 p-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 transition-colors shadow-sm cursor-pointer"
              aria-label="Help Guide"
              title="Help Guide"
            >
              <HelpCircle className="w-5 h-5" aria-hidden="true" />
            </button>
          </div>

        </div>
      </header>
    </>
  );
}

