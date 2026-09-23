import React from 'react';
import { History, Download, ShieldAlert, AlertCircle, Info } from 'lucide-react';

export default function AuditLog({ events, onExport }) {
  const getSeverityBadge = (severity) => {
    switch (severity) {
      case 'CRITICAL':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'WARNING':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  const getIcon = (severity) => {
    switch (severity) {
      case 'CRITICAL':
        return <ShieldAlert className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" aria-hidden="true" />;
      case 'WARNING':
        return <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" aria-hidden="true" />;
      default:
        return <Info className="w-5 h-5 text-slate-400 shrink-0 mt-0.5" aria-hidden="true" />;
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
    <section aria-labelledby="audit-log-heading" className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm transition-all flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-100">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-slate-100 text-slate-700 rounded-xl" aria-hidden="true">
              <History className="w-5 h-5" />
            </div>
            <div>
              <h2 id="audit-log-heading" className="text-base font-bold text-slate-900 tracking-tight m-0">
                Incident & Activity Log
              </h2>
              <span className="text-xs text-slate-500 font-medium">Real-time forensic telemetry stream</span>
            </div>
          </div>
          <button
            onClick={handleExportJson}
            className="text-sm font-semibold text-slate-700 hover:text-slate-900 flex items-center gap-2 px-3.5 py-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 transition shadow-2xs min-h-[40px] cursor-pointer"
            aria-label="Export audit log as JSON file"
          >
            <Download className="w-4 h-4 text-slate-500" aria-hidden="true" /> Export JSON
          </button>
        </div>

        {/* Scrollable Event Feed with Expanded Height */}
        <div className="space-y-3 max-h-[380px] overflow-y-auto pr-1" role="feed" aria-label="Incident stream entries">
          {events.length === 0 ? (
            <div className="text-center py-12 text-sm text-slate-500">
              No security incidents recorded in this session. Real-time protection is active.
            </div>
          ) : (
            events.map((evt, idx) => (
              <article
                key={idx}
                className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex items-start justify-between gap-3 text-sm transition hover:bg-slate-100/70"
                aria-label={`Event ${evt.event_type} at ${evt.time_str || new Date(evt.timestamp * 1000).toLocaleTimeString()}`}
              >
                <div className="flex items-start gap-3">
                  {getIcon(evt.severity)}
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-bold text-slate-900">{evt.event_type}</span>
                      <span
                        className={`text-xs font-bold px-2.5 py-0.5 rounded-full border uppercase ${getSeverityBadge(
                          evt.severity
                        )}`}
                      >
                        {evt.severity}
                      </span>
                    </div>
                    <div className="text-slate-700 text-sm mt-1 leading-normal font-normal">{evt.details}</div>
                  </div>
                </div>

                <time className="font-mono text-xs text-slate-500 font-medium whitespace-nowrap shrink-0 ml-2">
                  {evt.time_str || new Date(evt.timestamp * 1000).toLocaleTimeString()}
                </time>
              </article>
            ))
          )}
        </div>
      </div>
    </section>
  );
}
