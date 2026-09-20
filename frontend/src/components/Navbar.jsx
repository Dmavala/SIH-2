import React from 'react';
import { Shield, Mic, MicOff } from 'lucide-react';

export default function Navbar({
  isConnected,
  isMicActive,
  onToggleMic,
}) {
  return (
    <header className="border-b border-zinc-800/80 bg-zinc-950/90 backdrop-blur-md sticky top-0 z-40 px-6 py-3">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="p-2 bg-zinc-900 border border-zinc-800 rounded-lg text-zinc-100">
            <Shield className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold tracking-tight text-white">
                AEGIS
              </span>
              <span className="text-zinc-600 font-mono text-xs">/</span>
              <span className="text-xs font-mono text-zinc-400 tracking-wider">
                VOICE SENTINEL
              </span>
            </div>
          </div>
        </div>

        {/* Minimalist Controls */}
        <div className="flex items-center gap-4">
          {/* Connection Indicator */}
          <div className="flex items-center gap-2 text-xs font-mono text-zinc-500">
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isConnected ? 'bg-zinc-200' : 'bg-zinc-600'
              }`}
            />
            <span>{isConnected ? 'ONLINE' : 'OFFLINE'}</span>
          </div>

          {/* Minimalist Live Mic Button */}
          <button
            onClick={onToggleMic}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs transition-all font-mono ${
              isMicActive
                ? 'bg-white text-black font-semibold hover:bg-zinc-200'
                : 'border border-zinc-800 bg-zinc-900/90 text-zinc-300 hover:border-zinc-700 hover:bg-zinc-800 hover:text-white'
            }`}
            title="Toggle Live Audio Stream"
          >
            {isMicActive ? (
              <>
                <MicOff className="w-3.5 h-3.5" />
                <span>STOP MIC</span>
              </>
            ) : (
              <>
                <Mic className="w-3.5 h-3.5 text-zinc-400" />
                <span>START MIC</span>
              </>
            )}
          </button>
        </div>
      </div>
    </header>
  );
}
