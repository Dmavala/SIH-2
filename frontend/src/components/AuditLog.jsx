import React from 'react';
import { History, Download, ShieldAlert, AlertCircle, Info } from 'lucide-react';

export default function AuditLog({ events, onExport }) {
  const getSeverityBadge = (severity) => {
    switch (severity) {
      case 'CRITICAL':
        return 'bg-white text-black font-bold border-white';
      case 'WARNING':
        return 'bg-zinc-800 border-zinc-700 text-zinc-200';
      default:
        return 'bg-zinc-900 border-zinc-800 text-zinc-400';
    }
  };

  const getIcon = (severity) => {
    switch (severity) {
      case 'CRITICAL':
        return <ShieldAlert className="w-3.5 h-3.5 text-white shrink-0 mt-0.5" />;
      case 'WARNING':
        return <AlertCircle className="w-3.5 h-3.5 text-zinc-400 shrink-0 mt-0.5" />;
      default:
        return <Info className="w-3.5 h-3.5 text-zinc-500 shrink-0 mt-0.5" />;
    }
  };

  const handleExportJson = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(events, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `aegis_forensic_audit_${Date.now()}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="bg-zinc-950 border border-zinc-800/90 rounded-2xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-zinc-400" />
          <h2 className="text-xs uppercase font-mono tracking-wider text-zinc-400 m-0">
            Incident Stream & Audit Log
          </h2>
        </div>
        <button
          onClick={handleExportJson}
          className="text-[11px] font-mono text-zinc-300 hover:text-white flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-zinc-800 bg-zinc-900 hover:bg-zinc-800 transition"
        >
          <Download className="w-3 h-3 text-zinc-400" /> Export Log
        </button>
      </div>

      <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
        {events.length === 0 ? (
          <div className="text-center py-6 text-xs text-zinc-600 font-mono">
            No security incidents recorded. System active.
          </div>
        ) : (
          events.map((evt, idx) => (
            <div
              key={idx}
              className="p-2.5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 flex items-start justify-between gap-3 text-xs"
            >
              <div className="flex items-start gap-2.5">
                {getIcon(evt.severity)}
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-zinc-200">{evt.event_type}</span>
                    <span
                      className={`text-[9px] font-bold px-1.5 py-0.5 rounded border uppercase font-mono ${getSeverityBadge(
                        evt.severity
                      )}`}
                    >
                      {evt.severity}
                    </span>
                  </div>
                  <div className="text-zinc-400 text-[11px] mt-0.5">{evt.details}</div>
                </div>
              </div>

              <div className="font-mono text-[10px] text-zinc-500 whitespace-nowrap">
                {evt.time_str || new Date(evt.timestamp * 1000).toLocaleTimeString()}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
