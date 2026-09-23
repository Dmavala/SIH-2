import React, { useState, useRef, useEffect } from 'react';
import {
  Upload,
  FileAudio,
  Play,
  Pause,
  AlertTriangle,
  CheckCircle2,
  ShieldAlert,
  Scale,
  RefreshCw,
  PhoneCall,
  Activity,
  FileCheck,
  Waves,
  Sparkles,
  X,
  MessageSquare,
  Copy,
  Check,
  Quote,
  Shield,
  Info,
  Mic,
  MicOff,
  Radio,
} from 'lucide-react';
import { apiUrl } from '../config';

export default function FileAnalyzer({ onGenerateDossierForFile }) {
  const [file, setFile] = useState(null);
  const [telephonyMode, setTelephonyMode] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisStep, setAnalysisStep] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [copiedTranscript, setCopiedTranscript] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);

  const fileInputRef = useRef(null);
  const audioRef = useRef(null);
  const resultsRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerIntervalRef = useRef(null);

  // Smoothly scroll results into view when ready
  useEffect(() => {
    if (result && resultsRef.current) {
      resultsRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [result]);

  // Clean up recording timers
  useEffect(() => {
    return () => {
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop();
      }
    };
  }, []);

  const handleFileDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelected = (selectedFile) => {
    if (!selectedFile.type.startsWith('audio/') && !selectedFile.name.match(/\.(wav|mp3|flac|ogg|m4a)$/i)) {
      setError('Please select a valid audio file (.wav, .mp3, .flac, .ogg, .m4a)');
      return;
    }
    setFile(selectedFile);
    setError(null);
    setResult(null);
    setIsPlaying(false);
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
  };

  const handleStartRecording = async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };
      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        const now = new Date();
        const timeStr = `${now.getHours()}-${now.getMinutes()}-${now.getSeconds()}`;
        const recordedFile = new File(
          [audioBlob],
          `mic_recording_${timeStr}.wav`,
          { type: 'audio/wav' }
        );
        handleFileSelected(recordedFile);
        stream.getTracks().forEach((t) => t.stop());
      };
      mediaRecorder.start();
      mediaRecorderRef.current = mediaRecorder;
      setIsRecording(true);
      setRecordingSeconds(0);
      timerIntervalRef.current = setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      console.error('Microphone recording error:', err);
      setError('Could not access microphone to record voice sample. Check browser permissions.');
    }
  };

  const handleStopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
        timerIntervalRef.current = null;
      }
    }
  };

  const handleAnalyze = async () => {
    if (!file) return;
    setIsAnalyzing(true);
    setError(null);
    setAnalysisStep('Scanning acoustic neural envelopes & spectral anomalies...');

    const stepTimer1 = setTimeout(() => {
      setAnalysisStep('Decoding speech audio to text (STT)...');
    }, 1500);
    const stepTimer2 = setTimeout(() => {
      setAnalysisStep('Running AI semantic intent & threat reasoning...');
    }, 3500);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('telephony_mode', telephonyMode);

    try {
      const res = await fetch(apiUrl('/api/analyze-file'), {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Server returned ${res.status}`);
      }

      const data = await res.json();
      setResult(data);
      setAnalysisStep('Analysis complete');
    } catch (err) {
      console.error('File analysis failed:', err);
      setError(err.message || 'Failed to analyze audio file. Ensure backend server is running.');
    } finally {
      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);
      setIsAnalyzing(false);
    }
  };

  const togglePlayback = () => {
    if (!audioRef.current && file) {
      audioRef.current = new Audio(URL.createObjectURL(file));
      audioRef.current.onended = () => setIsPlaying(false);
    }
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
        setIsPlaying(false);
      } else {
        audioRef.current.play();
        setIsPlaying(true);
      }
    }
  };

  const handleClear = () => {
    setFile(null);
    setResult(null);
    setError(null);
    setIsPlaying(false);
    setCopiedTranscript(false);
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
  };

  const handleCopyTranscript = () => {
    if (!result?.transcript) return;
    navigator.clipboard.writeText(result.transcript);
    setCopiedTranscript(true);
    setTimeout(() => setCopiedTranscript(false), 2000);
  };

  const analysis = result?.analysis;
  const forensics = analysis?.forensics;
  const riskScore = analysis ? analysis.risk_score : 0;
  const isSynthetic = riskScore >= 60.0;

  return (
    <div className="space-y-6 max-w-6xl mx-auto w-full" role="region" aria-label="Audio File Forensic Analysis">
      {/* Top Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 rounded-2xl bg-white border border-slate-200 shadow-sm">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-slate-900 text-white rounded-2xl shrink-0 shadow-sm" aria-hidden="true">
            <FileAudio className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-extrabold text-slate-900 tracking-tight m-0">
              Audio File Forensics
            </h2>
            <p className="text-xs text-slate-500 font-medium mt-0.5 m-0">
              Upload recorded audio files to run multi-branch deepfake detection and verify biometrics
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 px-3.5 py-2 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 text-xs font-bold text-slate-700 cursor-pointer transition shadow-2xs">
            <input
              type="checkbox"
              checked={telephonyMode}
              onChange={(e) => setTelephonyMode(e.target.checked)}
              className="rounded text-indigo-600 focus:ring-indigo-500"
            />
            <PhoneCall className="w-3.5 h-3.5 text-slate-500" aria-hidden="true" />
            <span>Telephony Simulation (G.711)</span>
          </label>

          {file && (
            <button
              onClick={handleClear}
              className="px-3.5 py-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 text-xs font-bold flex items-center gap-1.5 transition shadow-2xs cursor-pointer"
              title="Clear Selected File"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Clear
            </button>
          )}
        </div>
      </div>

      {/* Hero Upload & Action Panel */}
      <div className="p-8 rounded-2xl bg-white border border-slate-200 shadow-sm flex flex-col items-center justify-center text-center transition-all">
        {isRecording ? (
          /* Live Recording Panel */
          <div className="w-full border-2 border-rose-300 bg-rose-50/60 rounded-2xl p-8 flex flex-col items-center justify-center animate-pulse">
            <div className="w-16 h-16 rounded-2xl bg-rose-600 text-white flex items-center justify-center shadow-lg mb-4">
              <Mic className="w-8 h-8 animate-bounce" />
            </div>
            <span className="text-base font-extrabold text-rose-950">
              Recording Voice Sample...
            </span>
            <span className="text-2xl font-black font-mono text-rose-600 mt-2">
              00:{recordingSeconds < 10 ? `0${recordingSeconds}` : recordingSeconds}
            </span>
            <p className="text-xs text-rose-700 font-medium mt-1 max-w-sm">
              Speak clearly into your microphone. Once finished, the recorded sample will be attached automatically for forensic analysis.
            </p>
            <button
              onClick={handleStopRecording}
              className="mt-5 px-6 py-3 bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs rounded-xl shadow-md transition cursor-pointer flex items-center gap-2"
            >
              <MicOff className="w-4 h-4" /> Stop & Use Recording
            </button>
          </div>
        ) : (
          /* Standard Dropzone */
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleFileDrop}
            onClick={() => fileInputRef.current?.click()}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                fileInputRef.current?.click();
              }
            }}
            tabIndex={0}
            role="button"
            aria-label="Upload audio file"
            className={`w-full border-2 border-dashed rounded-2xl p-8 flex flex-col items-center justify-center transition cursor-pointer ${
              file
                ? 'border-indigo-400 bg-indigo-50/40'
                : 'border-slate-200 hover:border-slate-400 bg-slate-50/50 hover:bg-slate-50'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".wav,.mp3,.flac,.ogg,.m4a,audio/*"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && handleFileSelected(e.target.files[0])}
            />

            <div
              className={`w-16 h-16 rounded-2xl flex items-center justify-center mb-4 transition-all ${
                file
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'bg-white border border-slate-200 text-slate-600 shadow-xs'
              }`}
            >
              {file ? <FileCheck className="w-8 h-8" /> : <Upload className="w-8 h-8" />}
            </div>

            {file ? (
              <div className="flex flex-col items-center">
                <span className="text-base font-extrabold text-slate-900">{file.name}</span>
                <span className="text-xs text-slate-500 font-semibold mt-1">
                  {(file.size / 1024 / 1024).toFixed(2)} MB • Ready for analysis
                </span>
                <span className="text-xs font-bold text-indigo-600 mt-2 hover:underline">
                  Click or drop another file to replace
                </span>
              </div>
            ) : (
              <div className="flex flex-col items-center">
                <span className="text-base font-extrabold text-slate-900">
                  Drag and drop your audio file here
                </span>
                <span className="text-xs font-semibold text-slate-500 mt-1">
                  or click to browse from your computer (WAV, MP3, FLAC, M4A, OGG)
                </span>
              </div>
            )}
          </div>
        )}

        {/* Alternative: Record Live Audio Clip Button when no file selected and not recording */}
        {!file && !isRecording && (
          <div className="mt-4 flex items-center gap-3">
            <span className="text-xs text-slate-400 font-medium">or</span>
            <button
              onClick={handleStartRecording}
              className="px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-bold flex items-center gap-2 transition shadow-2xs cursor-pointer"
            >
              <Mic className="w-4 h-4 text-rose-500" /> Record Voice Sample from Microphone
            </button>
          </div>
        )}

        {error && (
          <div className="w-full mt-4 p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-bold flex items-center gap-2" role="alert">
            <AlertTriangle className="w-4 h-4 shrink-0 text-rose-600" aria-hidden="true" />
            <span>{error}</span>
          </div>
        )}

        {/* Action Buttons Bar */}
        {file && (
          <div className="flex flex-col sm:flex-row items-center gap-3 w-full max-w-md mt-6">
            <button
              onClick={handleAnalyze}
              disabled={isAnalyzing}
              className="flex-1 w-full py-3.5 px-6 rounded-xl bg-slate-900 hover:bg-slate-800 disabled:bg-slate-200 disabled:text-slate-400 text-white text-sm font-bold flex items-center justify-center gap-2 shadow-sm transition cursor-pointer"
            >
              {isAnalyzing ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" /> Analyzing Audio...
                </>
              ) : (
                <>
                  <Activity className="w-4 h-4 text-indigo-400" /> Run Forensic Analysis
                </>
              )}
            </button>

            <button
              onClick={togglePlayback}
              className="w-full sm:w-auto py-3.5 px-5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-800 text-sm font-bold flex items-center justify-center gap-2 transition shadow-2xs cursor-pointer"
              title="Preview Audio"
            >
              {isPlaying ? <Pause className="w-4 h-4 text-slate-900" /> : <Play className="w-4 h-4 text-slate-700" />}
              <span>{isPlaying ? 'Pause' : 'Listen'}</span>
            </button>
          </div>
        )}

        {/* Real-time Multi-stage Analysis Progress Indicator */}
        {isAnalyzing && (
          <div className="w-full max-w-md mt-4 p-4 rounded-xl bg-indigo-50/70 border border-indigo-200 flex flex-col items-center gap-2.5 animate-in fade-in duration-150">
            <div className="flex items-center gap-2 text-indigo-950 font-bold text-xs">
              <RefreshCw className="w-3.5 h-3.5 animate-spin text-indigo-600" />
              <span>{analysisStep || 'Analyzing audio characteristics...'}</span>
            </div>
            <div className="w-full bg-indigo-200/60 rounded-full h-1.5 overflow-hidden">
              <div className="bg-indigo-600 h-full rounded-full animate-pulse w-4/5 transition-all duration-500"></div>
            </div>
            <div className="flex items-center justify-between w-full text-[10px] font-bold text-slate-400 uppercase tracking-wider mt-1 px-1">
              <span>1. Acoustic Scan</span>
              <span>2. STT Decode</span>
              <span>3. AI Reasoning</span>
            </div>
          </div>
        )}
      </div>

      {/* Analysis Results Display */}
      {result && analysis && (
        <div ref={resultsRef} className="space-y-6 pt-2 animate-in fade-in duration-200">
          
          {/* Top Result Banner */}
          <div
            className={`p-6 md:p-8 rounded-2xl border shadow-sm transition-all ${
              isSynthetic
                ? 'bg-rose-50/70 border-rose-200 text-rose-950'
                : 'bg-emerald-50/70 border-emerald-200 text-emerald-950'
            }`}
          >
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
              <div className="flex items-start gap-4">
                <div
                  className={`w-14 h-14 rounded-2xl flex items-center justify-center shrink-0 shadow-sm ${
                    isSynthetic ? 'bg-rose-100 text-rose-600' : 'bg-emerald-100 text-emerald-600'
                  }`}
                >
                  {isSynthetic ? <ShieldAlert className="w-8 h-8" /> : <CheckCircle2 className="w-8 h-8" />}
                </div>
                <div>
                  <div className="flex items-center gap-2.5 mb-1">
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider border ${
                        isSynthetic
                          ? 'bg-rose-100 text-rose-800 border-rose-200'
                          : 'bg-emerald-100 text-emerald-800 border-emerald-200'
                      }`}
                    >
                      Verdict
                    </span>
                    <span className="text-xs font-bold text-slate-500 font-mono">
                      Latency: {analysis.latency_ms}ms
                    </span>
                  </div>
                  <h3 className="text-2xl font-extrabold tracking-tight m-0 text-slate-900">
                    {analysis.label}
                  </h3>
                  <p className="text-xs text-slate-600 font-medium mt-1 m-0">
                    File: <span className="font-bold text-slate-900">{result.filename}</span> • Duration: <span className="font-bold text-slate-900">{result.duration_sec}s</span> • Model: <span className="font-bold text-slate-900">{analysis.model_architecture}</span>
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-5 self-end md:self-center">
                <div className="text-right">
                  <span className="text-xs text-slate-500 uppercase font-bold tracking-wider block">Threat Score</span>
                  <span className={`text-4xl font-extrabold tracking-tight ${isSynthetic ? 'text-rose-600' : 'text-emerald-600'}`}>
                    {riskScore.toFixed(1)}%
                  </span>
                </div>

                {onGenerateDossierForFile && (
                  <button
                    onClick={() =>
                      onGenerateDossierForFile({
                        session_id: `FILE-${result.filename.slice(0, 8).toUpperCase()}`,
                        threat_score: riskScore,
                        status: analysis.status,
                        forensics: forensics,
                        anomalies: analysis.anomalies || [],
                        model_consensus: {
                          aasist_prob: analysis.raw_neural_prob || riskScore / 100,
                          rawnet_prob: analysis.raw_neural_prob || riskScore / 100,
                          telephony_tested: telephonyMode,
                        },
                        case_metadata: {
                          case_no: `NCRP/FILE/${new Date().getFullYear()}/${result.filename.slice(0, 6).toUpperCase()}`,
                          fir_ref: isSynthetic
                            ? 'FIR REGISTERED UNDER SEC 66D IT ACT & SEC 318 BNS'
                            : 'CLEARED / AUTHENTIC EVIDENCE',
                          police_station: 'Cyber Crime Police Station (Audio Forensics Unit)',
                          officer: 'Inspector (Examiner of Electronic Records)',
                        },
                        transcript: result.transcript,
                        ai_analysis: result.ai_analysis,
                      })
                    }
                    className="py-3 px-5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold flex items-center gap-2 shadow-sm transition cursor-pointer"
                  >
                    <Scale className="w-4 h-4 text-indigo-400" /> Export Legal Certificate
                  </button>
                )}
              </div>
            </div>

            {/* Waveform Amplitude Profile Preview */}
            {result.waveform_preview && result.waveform_preview.length > 0 && (
              <div className="mt-6 pt-5 border-t border-slate-200/80">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                    <Waves className="w-3.5 h-3.5 text-indigo-600" /> Audio Amplitude Profile
                  </span>
                  <span className="text-[10px] uppercase font-bold text-slate-500 font-mono">128 Bins</span>
                </div>
                <div className="h-12 bg-white/90 border border-slate-200 rounded-xl p-2 flex items-center justify-between gap-0.5 shadow-2xs">
                  {result.waveform_preview.map((val, idx) => {
                    const heightPercent = Math.min(100, Math.max(10, Math.abs(val) * 100));
                    return (
                      <div
                        key={idx}
                        className={`flex-1 rounded-full transition-all ${
                          isSynthetic ? 'bg-rose-500' : 'bg-indigo-600'
                        }`}
                        style={{ height: `${heightPercent}%` }}
                      />
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Forensic Biometrics Grid */}
          {forensics && (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5">
              <div className="p-4 rounded-2xl bg-white border border-slate-200 shadow-xs">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Vocal Jitter</span>
                <span className="text-lg font-extrabold text-slate-900 mt-1 block">
                  {(forensics.jitter_local * 100).toFixed(3)}%
                </span>
                <span className="text-[11px] text-slate-500 font-medium mt-1 block">
                  {forensics.jitter_local < 0.0035 ? 'Unnatural robotic pitch stability' : 'Natural vocal cord micro-tremor'}
                </span>
              </div>

              <div className="p-4 rounded-2xl bg-white border border-slate-200 shadow-xs">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Noise Floor</span>
                <span className="text-lg font-extrabold text-slate-900 mt-1 block">
                  {forensics.ambient_noise_floor_db.toFixed(1)} dB
                </span>
                <span className="text-[11px] text-slate-500 font-medium mt-1 block">
                  {forensics.ambient_noise_floor_db < -65 ? 'Sterile digital vacuum' : 'Natural ambient room reverberation'}
                </span>
              </div>

              <div className="p-4 rounded-2xl bg-white border border-slate-200 shadow-xs">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Phase Dispersion</span>
                <span className="text-lg font-extrabold text-slate-900 mt-1 block">
                  {forensics.phase_dispersion.toFixed(4)}
                </span>
                <span className="text-[11px] text-slate-500 font-medium mt-1 block">
                  Neural vocoder soundwave artifacts
                </span>
              </div>

              <div className="p-4 rounded-2xl bg-white border border-slate-200 shadow-xs">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Pitch Mean</span>
                <span className="text-lg font-extrabold text-slate-900 mt-1 block">
                  {forensics.pitch_mean.toFixed(1)} Hz
                </span>
                <span className="text-[11px] text-slate-500 font-medium mt-1 block">
                  Fundamental speaking frequency
                </span>
              </div>

              <div className="p-4 rounded-2xl bg-white border border-slate-200 shadow-xs">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Vocal Shimmer</span>
                <span className="text-lg font-extrabold text-slate-900 mt-1 block">
                  {(forensics.shimmer_local * 100).toFixed(2)}%
                </span>
                <span className="text-[11px] text-slate-500 font-medium mt-1 block">
                  Cycle-to-cycle amplitude perturbation
                </span>
              </div>

              <div className="p-4 rounded-2xl bg-white border border-slate-200 shadow-xs">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Speech Ratio</span>
                <span className="text-lg font-extrabold text-slate-900 mt-1 block">
                  {(forensics.speech_ratio * 100).toFixed(0)}%
                </span>
                <span className="text-[11px] text-slate-500 font-medium mt-1 block">
                  Voice activity detection fraction
                </span>
              </div>
            </div>
          )}

          {/* Detected Anomalies */}
          {analysis.anomalies && analysis.anomalies.length > 0 && (
            <div className="p-5 rounded-2xl bg-rose-50 border border-rose-200 shadow-xs">
              <span className="text-xs font-bold text-rose-800 uppercase tracking-wider mb-2.5 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-600" /> Detected Synthetic Markers:
              </span>
              <div className="flex flex-wrap gap-2 mt-2">
                {analysis.anomalies.map((anom, i) => (
                  <span
                    key={i}
                    className="px-3 py-1.5 rounded-lg bg-white border border-rose-200 text-rose-800 text-xs font-bold shadow-2xs"
                  >
                    {anom}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Decoded Speech-to-Text Transcription Panel */}
          <div className="p-6 md:p-7 rounded-2xl bg-white border border-slate-200 shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-slate-100 text-slate-800" aria-hidden="true">
                  <MessageSquare className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-base font-extrabold text-slate-900 tracking-tight m-0">
                    Decoded Speech Transcription (STT)
                  </h4>
                  <p className="text-xs text-slate-500 font-medium mt-0.5 m-0">
                    Audio stream decoded and converted to text via real speech-to-text processing
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2.5">
                <span className="px-3 py-1 rounded-full text-xs font-bold bg-slate-100 text-slate-700 border border-slate-200">
                  {result.stt_info?.stt_engine || 'Google Web Speech STT'}
                </span>
                {result.transcript && (
                  <span className="px-2.5 py-1 rounded-full text-xs font-bold font-mono bg-indigo-50 text-indigo-700 border border-indigo-200">
                    {result.stt_info?.word_count || result.transcript.split(' ').length} words
                  </span>
                )}
                {result.transcript && (
                  <button
                    onClick={handleCopyTranscript}
                    className="px-3 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-bold flex items-center gap-1.5 transition shadow-2xs cursor-pointer"
                    title="Copy full transcript"
                  >
                    {copiedTranscript ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-600" /> Copied
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5 text-slate-500" /> Copy
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>

            {result.transcript ? (
              <div className="relative p-5 rounded-xl bg-slate-50 border border-slate-200/80 text-slate-900 text-sm font-medium leading-relaxed font-sans select-text">
                <Quote className="w-4 h-4 text-slate-400 absolute top-3.5 left-3.5 opacity-40 pointer-events-none" />
                <p className="pl-6 m-0 text-slate-800">
                  "{result.transcript}"
                </p>
              </div>
            ) : (
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-slate-500 text-xs font-semibold flex items-center gap-2">
                <Info className="w-4 h-4 text-slate-400 shrink-0" />
                <span>
                  {result.stt_info?.error || 'No verbal speech detected in audio file (pure acoustic tone or ambient carrier).'}
                </span>
              </div>
            )}
          </div>

          {/* AI Semantic Threat & Behavioral Intelligence */}
          {result.ai_analysis && (
            <div className="p-6 md:p-8 rounded-2xl bg-white border border-slate-200 shadow-sm space-y-6">
              
              {/* Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100" aria-hidden="true">
                    <Sparkles className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="text-base font-extrabold text-slate-900 tracking-tight m-0 flex items-center gap-2">
                      AI Semantic Threat & Behavioral Intelligence
                    </h4>
                    <p className="text-xs text-slate-500 font-medium mt-0.5 m-0">
                      Linguistic intent profiling, coercion detection, and social engineering risk analysis
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2.5">
                  <span className="px-3 py-1 rounded-full text-xs font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
                    {result.ai_analysis.ai_engine || 'Aegis Forensic Neural NLP'}
                  </span>
                  {result.ai_analysis.urgency_level && (
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-extrabold uppercase tracking-wide border ${
                        result.ai_analysis.urgency_level === 'CRITICAL'
                          ? 'bg-rose-100 text-rose-800 border-rose-200'
                          : result.ai_analysis.urgency_level === 'HIGH'
                          ? 'bg-amber-100 text-amber-800 border-amber-200'
                          : result.ai_analysis.urgency_level === 'MEDIUM'
                          ? 'bg-blue-100 text-blue-800 border-blue-200'
                          : 'bg-emerald-100 text-emerald-800 border-emerald-200'
                      }`}
                    >
                      {result.ai_analysis.urgency_level} URGENCY
                    </span>
                  )}
                </div>
              </div>

              {/* Threat Overview Grid */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                
                {/* Intent Category Card */}
                <div className="p-5 rounded-xl bg-slate-50 border border-slate-200/80 md:col-span-2">
                  <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                    Detected Intent Category
                  </span>
                  <h5 className="text-lg font-extrabold text-slate-900 mt-1 m-0">
                    {result.ai_analysis.intent_category || 'General Conversation'}
                  </h5>
                  <p className="text-xs text-slate-600 font-medium mt-2 m-0 leading-relaxed">
                    {result.ai_analysis.summary || 'Caller discourse analyzed against cyber fraud patterns.'}
                  </p>
                </div>

                {/* Threat Intent Score Card */}
                <div className="p-5 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col justify-between">
                  <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                    Semantic Threat Score
                  </span>
                  <div className="my-2">
                    <span
                      className={`text-3xl font-extrabold tracking-tight ${
                        result.ai_analysis.threat_intent_score >= 60
                          ? 'text-rose-600'
                          : result.ai_analysis.threat_intent_score >= 35
                          ? 'text-amber-600'
                          : 'text-emerald-600'
                      }`}
                    >
                      {result.ai_analysis.threat_intent_score}%
                    </span>
                    <span className="text-xs text-slate-500 font-semibold block mt-0.5">
                      Malicious intent confidence
                    </span>
                  </div>
                  {/* Progress bar */}
                  <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                    <div
                      className={`h-2 rounded-full transition-all ${
                        result.ai_analysis.threat_intent_score >= 60
                          ? 'bg-rose-500'
                          : result.ai_analysis.threat_intent_score >= 35
                          ? 'bg-amber-500'
                          : 'bg-emerald-500'
                      }`}
                      style={{ width: `${Math.min(100, Math.max(5, result.ai_analysis.threat_intent_score))}%` }}
                    />
                  </div>
                </div>

              </div>

              {/* Psychological Manipulation Tactics */}
              {result.ai_analysis.tactics && result.ai_analysis.tactics.length > 0 && (
                <div>
                  <span className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-2.5">
                    Psychological Manipulation & Social Engineering Tactics:
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {result.ai_analysis.tactics.map((tactic, idx) => (
                      <span
                        key={idx}
                        className="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200/70 border border-slate-200 text-slate-800 text-xs font-bold shadow-2xs transition"
                      >
                        {tactic}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Verbatim Coercive Phrases Highlight */}
              {result.ai_analysis.coercive_quotes && result.ai_analysis.coercive_quotes.length > 0 && (
                <div className="space-y-2.5">
                  <span className="text-xs font-bold text-rose-800 uppercase tracking-wider flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-rose-600" /> Flagged Coercive Statements (From Audio):
                  </span>
                  <div className="grid grid-cols-1 gap-2">
                    {result.ai_analysis.coercive_quotes.map((quote, idx) => (
                      <div
                        key={idx}
                        className="p-3.5 rounded-xl bg-rose-50/60 border border-rose-200/80 border-l-4 border-l-rose-500 text-slate-800 text-xs font-semibold leading-relaxed"
                      >
                        "{quote}"
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Linguistic & Syntactic Markers */}
              {result.ai_analysis.linguistic_markers && (
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 text-xs">
                  <span className="font-bold text-slate-700 uppercase tracking-wider block mb-1">
                    Linguistic & Cadence Analysis:
                  </span>
                  <p className="text-slate-600 font-medium m-0 leading-relaxed">
                    {result.ai_analysis.linguistic_markers}
                  </p>
                </div>
              )}

              {/* Actionable Protective Protocol Advisory */}
              {result.ai_analysis.guidance && (
                <div
                  className={`p-5 rounded-2xl border flex items-start gap-3.5 shadow-xs ${
                    result.ai_analysis.threat_intent_score >= 50
                      ? 'bg-rose-50/80 border-rose-200 text-rose-950'
                      : 'bg-emerald-50/80 border-emerald-200 text-emerald-950'
                  }`}
                >
                  <ShieldAlert
                    className={`w-5 h-5 shrink-0 mt-0.5 ${
                      result.ai_analysis.threat_intent_score >= 50 ? 'text-rose-600' : 'text-emerald-600'
                    }`}
                  />
                  <div>
                    <span className="text-xs font-extrabold uppercase tracking-wider block">
                      Protective Security Advisory (CERT-In / I4C Protocol):
                    </span>
                    <p className="text-xs font-semibold mt-1 m-0 leading-relaxed">
                      {result.ai_analysis.guidance}
                    </p>
                  </div>
                </div>
              )}

            </div>
          )}

        </div>
      )}
    </div>
  );
}
