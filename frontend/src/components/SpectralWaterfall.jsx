import React, { useEffect, useRef } from 'react';
import { Activity, Waves, BarChart3 } from 'lucide-react';

export default function SpectralWaterfall({ waveform, spectral, isSynthetic }) {
  const waveCanvasRef = useRef(null);
  const specCanvasRef = useRef(null);
  const waterfallHistoryRef = useRef([]);

  // Auto-resize canvas buffers to match element client dimensions with HiDPI support
  const resizeCanvasToDisplaySize = (canvas) => {
    if (!canvas) return { width: 300, height: 150 };
    const width = canvas.clientWidth || 300;
    const height = canvas.clientHeight || 150;
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }
    return { width, height };
  };

  // 1. Draw Waveform Oscilloscope
  useEffect(() => {
    const canvas = waveCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const { width, height } = resizeCanvasToDisplaySize(canvas);

    // Clean background
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, width, height);

    // Subtle horizontal grid lines
    ctx.strokeStyle = '#f1f5f9';
    ctx.lineWidth = 1;
    [0.25, 0.5, 0.75].forEach((pos) => {
      ctx.beginPath();
      ctx.moveTo(0, height * pos);
      ctx.lineTo(width, height * pos);
      ctx.stroke();
    });

    // Zero-line axis
    ctx.strokeStyle = '#e2e8f0';
    ctx.beginPath();
    ctx.moveTo(0, height / 2);
    ctx.lineTo(width, height / 2);
    ctx.stroke();

    if (!waveform || waveform.length === 0) {
      ctx.strokeStyle = '#cbd5e1';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(0, height / 2);
      ctx.lineTo(width, height / 2);
      ctx.stroke();
      return;
    }

    // High-resolution waveform path
    ctx.lineWidth = 2.5;
    ctx.strokeStyle = isSynthetic ? '#ef4444' : '#4f46e5';
    ctx.beginPath();

    const sliceWidth = width / (waveform.length - 1);
    waveform.forEach((val, i) => {
      const x = i * sliceWidth;
      const y = (1 - val) * (height / 2);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
  }, [waveform, isSynthetic]);

  // 2. Draw Spectral Frequency Waterfall
  useEffect(() => {
    const canvas = specCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const { width, height } = resizeCanvasToDisplaySize(canvas);

    if (spectral && spectral.length > 0) {
      waterfallHistoryRef.current.unshift([...spectral]);
      if (waterfallHistoryRef.current.length > 36) {
        waterfallHistoryRef.current.pop();
      }
    }

    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, width, height);

    const history = waterfallHistoryRef.current;
    if (history.length === 0) {
      // Empty grid lines
      ctx.strokeStyle = '#f1f5f9';
      ctx.lineWidth = 1;
      [0.25, 0.5, 0.75].forEach((pos) => {
        ctx.beginPath();
        ctx.moveTo(0, height * pos);
        ctx.lineTo(width, height * pos);
        ctx.stroke();
      });
      return;
    }

    const rowHeight = height / 36;
    const numBands = history[0].length;
    const colWidth = width / numBands;

    history.forEach((row, rowIdx) => {
      const y = rowIdx * rowHeight;
      row.forEach((mag, colIdx) => {
        const x = colIdx * colWidth;
        const normalized = Math.min(1.0, Math.max(0.0, mag * 1.6));

        if (isSynthetic) {
          // Rose/Crimson thermal spectral gradient for synthetic vocoders
          const intensity = Math.floor(normalized * 220);
          const r = 255;
          const g = Math.max(0, 245 - intensity);
          const b = Math.max(0, 245 - intensity);
          ctx.fillStyle = `rgb(${r}, ${g}, ${b})`;
        } else {
          // Elegant indigo/slate density gradient for organic speech
          const intensity = Math.floor(normalized * 220);
          const r = Math.max(15, 248 - Math.floor(intensity * 0.9));
          const g = Math.max(23, 250 - Math.floor(intensity * 0.85));
          const b = Math.max(42, 255 - Math.floor(intensity * 0.3));
          ctx.fillStyle = `rgb(${r}, ${g}, ${b})`;
        }

        ctx.fillRect(x, y, colWidth + 0.5, rowHeight + 0.5);
      });
    });

    // 3.5 kHz acoustic telephony boundary
    const splitX = (14 / numBands) * width;
    ctx.strokeStyle = '#94a3b8';
    ctx.setLineDash([3, 3]);
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(splitX, 0);
    ctx.lineTo(splitX, height);
    ctx.stroke();
    ctx.setLineDash([]);
  }, [spectral, isSynthetic]);

  return (
    <div className="flex flex-col h-full w-full gap-3">
      {/* Telemetry Legend */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-indigo-600" />
          <span className="text-xs font-bold text-slate-800 tracking-tight">
            Realtime Signal & Spectrogram Telemetry
          </span>
        </div>
        <div className="flex items-center gap-4 text-xs font-semibold text-slate-500">
          <span className="flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${isSynthetic ? 'bg-rose-500' : 'bg-indigo-600'}`}></span>
            Vocal Trajectory
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-slate-400"></span>
            3.5 kHz Cutoff
          </span>
        </div>
      </div>

      {/* Two Balanced Signal Windows */}
      <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-4 min-h-0">
        {/* Oscilloscope */}
        <div className="flex flex-col h-full bg-slate-50/50 rounded-2xl border border-slate-200 p-3 shadow-inner">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
              <Waves className="w-3.5 h-3.5 text-indigo-500" /> Live Waveform (16 kHz PCM)
            </span>
            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider font-mono">Time Domain</span>
          </div>
          <div className="flex-1 w-full rounded-xl bg-white border border-slate-200 overflow-hidden relative shadow-xs min-h-[160px]">
            <canvas ref={waveCanvasRef} className="absolute inset-0 w-full h-full block" />
          </div>
        </div>

        {/* Spectrogram Waterfall */}
        <div className="flex flex-col h-full bg-slate-50/50 rounded-2xl border border-slate-200 p-3 shadow-inner">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
              <BarChart3 className="w-3.5 h-3.5 text-indigo-500" /> Frequency Waterfall (FFT)
            </span>
            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider font-mono">0 - 8 kHz</span>
          </div>
          <div className="flex-1 w-full rounded-xl bg-white border border-slate-200 overflow-hidden relative shadow-xs min-h-[160px]">
            <canvas ref={specCanvasRef} className="absolute inset-0 w-full h-full block" />
            <div className="absolute bottom-2.5 left-1/2 -translate-x-1/2 flex items-center justify-center text-[10px] font-bold text-slate-600 bg-white/90 border border-slate-200 px-2.5 py-0.5 rounded-full shadow-xs whitespace-nowrap">
              3.5 kHz Telephony Cutoff
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
