import React, { useEffect, useRef } from 'react';
import { Activity } from 'lucide-react';

export default function SpectralWaterfall({ waveform, spectral, isSynthetic }) {
  const waveCanvasRef = useRef(null);
  const specCanvasRef = useRef(null);
  const waterfallHistoryRef = useRef([]);

  // Draw Waveform Oscilloscope
  useEffect(() => {
    const canvas = waveCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    ctx.clearRect(0, 0, width, height);

    // Center grid line
    ctx.strokeStyle = '#18181b';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, height / 2);
    ctx.lineTo(width, height / 2);
    ctx.stroke();

    if (!waveform || waveform.length === 0) {
      ctx.strokeStyle = '#27272a';
      ctx.beginPath();
      ctx.moveTo(0, height / 2);
      ctx.lineTo(width, height / 2);
      ctx.stroke();
      return;
    }

    // Monochromatic waveform line
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = '#f4f4f5';
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

  // Draw Grayscale Spectral Waterfall
  useEffect(() => {
    const canvas = specCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    if (spectral && spectral.length > 0) {
      waterfallHistoryRef.current.unshift([...spectral]);
      if (waterfallHistoryRef.current.length > 32) {
        waterfallHistoryRef.current.pop();
      }
    }

    ctx.clearRect(0, 0, width, height);

    const history = waterfallHistoryRef.current;
    if (history.length === 0) {
      ctx.fillStyle = '#09090b';
      ctx.fillRect(0, 0, width, height);
      return;
    }

    const rowHeight = height / 32;
    const numBands = history[0].length;
    const colWidth = width / numBands;

    history.forEach((row, rowIdx) => {
      const y = rowIdx * rowHeight;
      row.forEach((mag, colIdx) => {
        const x = colIdx * colWidth;
        const normalized = Math.min(1.0, Math.max(0.0, mag * 1.5));

        // Grayscale luminescence mapping (pure dark -> gray -> pure white)
        const grayVal = Math.floor(normalized * 255);
        ctx.fillStyle = `rgb(${grayVal}, ${grayVal}, ${grayVal})`;
        ctx.fillRect(x, y, colWidth + 0.5, rowHeight + 0.5);
      });
    });

    // Clean boundary line (3.5kHz boundary)
    const splitX = (14 / numBands) * width;
    ctx.strokeStyle = '#71717a';
    ctx.setLineDash([3, 3]);
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(splitX, 0);
    ctx.lineTo(splitX, height);
    ctx.stroke();
    ctx.setLineDash([]);
  }, [spectral, isSynthetic]);

  return (
    <div className="bg-zinc-950 border border-zinc-800/90 rounded-2xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-zinc-400" />
          <h2 className="text-xs uppercase font-mono tracking-wider text-zinc-400 m-0">
            Real-Time Spectral & Phase Forensics
          </h2>
        </div>
        <div className="flex items-center gap-4 text-[11px] font-mono text-zinc-500">
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-zinc-600 inline-block"></span> 0 - 3.5 kHz (Vocal Tract)
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-zinc-300 inline-block"></span> 3.5 - 8.0 kHz (Artifact Zone)
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Oscilloscope Waveform */}
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between text-[11px] text-zinc-500 font-mono">
            <span>OSCILLOSCOPE WAVEFORM</span>
            <span>16 kHz PCM</span>
          </div>
          <div className="bg-black rounded-xl p-2 border border-zinc-900 overflow-hidden">
            <canvas
              ref={waveCanvasRef}
              width={400}
              height={140}
              className="w-full h-[140px] block"
            />
          </div>
        </div>

        {/* Spectral Waterfall */}
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between text-[11px] text-zinc-500 font-mono">
            <span>SPECTRAL WATERFALL</span>
            <span>LFCC Linear Bands</span>
          </div>
          <div className="bg-black rounded-xl p-2 border border-zinc-900 overflow-hidden relative">
            <canvas
              ref={specCanvasRef}
              width={400}
              height={140}
              className="w-full h-[140px] block"
            />
            {/* Frequency Axis Marker */}
            <div className="absolute bottom-3 left-4 right-4 flex justify-between text-[9px] font-mono text-zinc-500 bg-black/80 px-2 py-0.5 rounded pointer-events-none">
              <span>0 Hz</span>
              <span>1.5 kHz</span>
              <span className="text-zinc-300">3.5 kHz</span>
              <span>8.0 kHz</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
