import React, { useState } from 'react';
import {
  Scale,
  Search,
  Download,
  FileText,
  Clock,
  Hash,
  RefreshCw,
  Filter,
  CheckCircle2,
  AlertTriangle,
  ShieldAlert,
} from 'lucide-react';

export default function CaseAuditPortal({
  events = [],
  onRefresh,
  onOpenDossierWithCustomMeta,
  currentRisk = 0,
  currentStatus = 'AUTHENTIC_HUMAN',
  forensics = null,
  anomalies = [],
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [severityFilter, setSeverityFilter] = useState('ALL');

  // Custom Case Metadata State for Section 63 BSA Certificate
  const [caseNo, setCaseNo] = useState(
    `NCRP/CYBER/${new Date().getFullYear()}/DEL-${Math.floor(100000 + Math.random() * 900000)}`
  );
  const [firRef, setFirRef] = useState('FIR NO. 142/2026 U/S 66D IT ACT & SEC 318 BNS');
  const [policeStation, setPoliceStation] = useState('Cyber Crime Police Station, Special Cell, New Delhi');
  const [officerName, setOfficerName] = useState('Inspector (Digital Evidence Examiner)');

  // Filter events
  const filteredEvents = events.filter((ev) => {
    const matchesSearch =
      (ev.event_type || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (ev.details || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (ev.session_id || '').toLowerCase().includes(searchTerm.toLowerCase());
    const matchesSeverity = severityFilter === 'ALL' || ev.severity === severityFilter;
    return matchesSearch && matchesSeverity;
  });

  const handleExportJson = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(events, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `Cyber_Audit_Ledger_${new Date().toISOString().slice(0, 10)}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const handleGenerateCertificate = () => {
    if (onOpenDossierWithCustomMeta) {
      onOpenDossierWithCustomMeta({
        case_no: caseNo,
        fir_ref: firRef,
        police_station: policeStation,
        officer: officerName,
      });
    }
  };

  const getSeverityBadge = (sev) => {
    switch (sev) {
      case 'CRITICAL':
        return 'bg-rose-100 text-rose-800 border-rose-200';
      case 'WARNING':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto w-full" role="region" aria-label="Incident Audit Ledger & Reports">
      {/* Top Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 rounded-2xl bg-white border border-slate-200 shadow-sm">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-slate-900 text-white rounded-2xl shrink-0 shadow-sm" aria-hidden="true">
            <Scale className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-extrabold text-slate-900 tracking-tight m-0">
              Audit Logs & Legal Reports
            </h2>
            <p className="text-xs text-slate-500 font-medium mt-0.5 m-0">
              Tamper-evident chain of custody ledger and Section 63 BSA certificate generator
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={onRefresh}
            className="px-4 py-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-bold flex items-center gap-2 transition shadow-2xs cursor-pointer"
            title="Refresh Incident Log"
          >
            <RefreshCw className="w-3.5 h-3.5 text-slate-500" /> Refresh
          </button>
          <button
            onClick={handleExportJson}
            className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold flex items-center gap-2 transition shadow-sm cursor-pointer"
            title="Download Tamper-Evident JSON Ledger"
          >
            <Download className="w-3.5 h-3.5" /> Export Ledger
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Official Court Certificate Builder Form */}
        <div className="lg:col-span-5 space-y-5">
          <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-sm space-y-5">
            <div className="flex items-center gap-2.5 border-b border-slate-100 pb-4">
              <FileText className="w-5 h-5 text-indigo-600" />
              <div>
                <h3 className="text-base font-extrabold text-slate-900 m-0">
                  Case Details
                </h3>
                <p className="text-[11px] text-slate-500 font-medium m-0 mt-0.5">
                  Metadata for court-admissible forensic certificate
                </p>
              </div>
            </div>

            <div className="space-y-4 text-xs">
              <div>
                <label
                  htmlFor="case-ref-input"
                  className="font-bold uppercase tracking-wider text-slate-600 block mb-1.5"
                >
                  Case Reference Number
                </label>
                <input
                  id="case-ref-input"
                  type="text"
                  value={caseNo}
                  onChange={(e) => setCaseNo(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-slate-900 font-bold focus:outline-none focus:border-slate-400 focus:bg-white text-xs transition shadow-inner"
                />
              </div>

              <div>
                <label
                  htmlFor="fir-ref-input"
                  className="font-bold uppercase tracking-wider text-slate-600 block mb-1.5"
                >
                  FIR / Crime Reference
                </label>
                <input
                  id="fir-ref-input"
                  type="text"
                  value={firRef}
                  onChange={(e) => setFirRef(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-slate-900 font-bold focus:outline-none focus:border-slate-400 focus:bg-white text-xs transition shadow-inner"
                />
              </div>

              <div>
                <label
                  htmlFor="police-station-input"
                  className="font-bold uppercase tracking-wider text-slate-600 block mb-1.5"
                >
                  Police Station / Cyber Unit
                </label>
                <input
                  id="police-station-input"
                  type="text"
                  value={policeStation}
                  onChange={(e) => setPoliceStation(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-slate-900 font-bold focus:outline-none focus:border-slate-400 focus:bg-white text-xs transition shadow-inner"
                />
              </div>

              <div>
                <label
                  htmlFor="officer-name-input"
                  className="font-bold uppercase tracking-wider text-slate-600 block mb-1.5"
                >
                  Investigating Officer / Examiner
                </label>
                <input
                  id="officer-name-input"
                  type="text"
                  value={officerName}
                  onChange={(e) => setOfficerName(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-slate-900 font-bold focus:outline-none focus:border-slate-400 focus:bg-white text-xs transition shadow-inner"
                />
              </div>
            </div>

            <div className="pt-2">
              <button
                onClick={handleGenerateCertificate}
                className="w-full py-3.5 px-5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold flex items-center justify-center gap-2 shadow-sm transition cursor-pointer"
                aria-label="Generate Section 63 BSA legal certificate"
              >
                <Scale className="w-4 h-4 text-indigo-400" /> Generate Section 63 Certificate
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Real-Time Incident Stream & Filterable Ledger */}
        <div className="lg:col-span-7 space-y-4">
          {/* Search & Filter Toolbar */}
          <div className="flex flex-col sm:flex-row gap-3 p-3.5 rounded-2xl bg-white border border-slate-200 shadow-sm items-center">
            <div className="relative flex-1 w-full">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" aria-hidden="true" />
              <input
                type="text"
                placeholder="Search events, session IDs, or forensic details..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                aria-label="Filter events by keyword"
                className="w-full pl-10 pr-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-slate-400 focus:bg-white transition"
              />
            </div>
            <div className="flex items-center gap-1 shrink-0" role="group" aria-label="Severity filter">
              {['ALL', 'CRITICAL', 'WARNING', 'INFO'].map((sev) => (
                <button
                  key={sev}
                  onClick={() => setSeverityFilter(sev)}
                  aria-pressed={severityFilter === sev}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition cursor-pointer ${
                    severityFilter === sev
                      ? 'bg-slate-900 text-white shadow-2xs'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {sev}
                </button>
              ))}
            </div>
          </div>

          {/* Incident Timeline Feed */}
          <div
            role="feed"
            aria-label="Incident Audit Ledger Feed"
            className="space-y-3 max-h-[560px] overflow-y-auto pr-1 custom-scrollbar"
          >
            {filteredEvents.length === 0 ? (
              <div className="p-12 text-center rounded-2xl border border-slate-200 bg-white text-xs text-slate-500 shadow-sm font-medium flex flex-col items-center justify-center gap-2">
                <Search className="w-6 h-6 text-slate-300" />
                <span>No recorded incidents match the search criteria.</span>
              </div>
            ) : (
              filteredEvents.map((ev, index) => (
                <article
                  key={ev.id || index}
                  aria-label={`${ev.event_type} incident with ${ev.severity} severity`}
                  className="p-4 rounded-2xl border border-slate-200 bg-white hover:border-slate-300 transition text-xs space-y-2 shadow-2xs"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${getSeverityBadge(ev.severity)}`}>
                        {ev.severity || 'INFO'}
                      </span>
                      <span className="font-extrabold text-slate-900">{ev.event_type}</span>
                    </div>
                    <time
                      dateTime={new Date(ev.timestamp * 1000).toISOString()}
                      className="flex items-center gap-1.5 text-slate-400 text-[11px] font-mono font-medium"
                    >
                      <Clock className="w-3 h-3" aria-hidden="true" />
                      <span>{new Date(ev.timestamp * 1000).toLocaleTimeString()}</span>
                    </time>
                  </div>

                  <p className="text-slate-700 leading-relaxed text-xs font-medium m-0">{ev.details}</p>

                  <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-100 text-[11px] text-slate-500">
                    <div>
                      Session: <span className="font-mono text-slate-800 font-bold">{ev.session_id}</span>
                    </div>
                    {ev.hash && (
                      <div className="flex items-center gap-1 text-slate-600 font-mono">
                        <Hash className="w-3 h-3 text-slate-400" aria-hidden="true" />
                        <span>SHA: {ev.hash.slice(0, 12)}...</span>
                      </div>
                    )}
                  </div>
                </article>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
