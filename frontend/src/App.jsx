import React, { useState, useEffect, useRef } from 'react';
import Navbar from './components/Navbar';
import ThreatMeter from './components/ThreatMeter';
import SpectralWaterfall from './components/SpectralWaterfall';
import AcousticForensics from './components/AcousticForensics';
import PreventionModal from './components/PreventionModal';
import AuditLog from './components/AuditLog';
import { apiUrl, getWebSocketUrl } from './config';

export default function App() {
  // WebSocket State
  const [isConnected, setIsConnected] = useState(false);
  const [sessionId, setSessionId] = useState('');
  const wsRef = useRef(null);

  // Telemetry State
  const [smoothedRisk, setSmoothedRisk] = useState(6.0);
  const [instantRisk, setInstantRisk] = useState(6.0);
  const [status, setStatus] = useState('AUTHENTIC_HUMAN');
  const [label, setLabel] = useState('AUTHENTIC HUMAN BIOMETRICS');
  const [color, setColor] = useState('green');
  const [anomalies, setAnomalies] = useState([]);
  const [forensics, setForensics] = useState(null);
  const [latencyMs, setLatencyMs] = useState(21.4);
  const [waveform, setWaveform] = useState([]);
  const [spectral, setSpectral] = useState([]);

  // In-Call Prevention State
  const [isFrozen, setIsFrozen] = useState(false);
  const [activeChallenge, setActiveChallenge] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Settings & Controls
  const [telephonyMode, setTelephonyMode] = useState(false);
  const [isMicActive, setIsMicActive] = useState(false);
  const [activeModel, setActiveModel] = useState('AASIST');
  const [auditEvents, setAuditEvents] = useState([]);

  // Audio Processing Refs
  const audioContextRef = useRef(null);
  const micStreamRef = useRef(null);
  const micProcessorRef = useRef(null);

  // 1. Fetch Health and Audit Log on mount
  useEffect(() => {
    fetch(apiUrl('/api/health'))
      .then((res) => res.json())
      .then((data) => {
        if (data.active_model) setActiveModel(data.active_model);
      })
      .catch((err) => console.error('Error fetching health:', err));

    fetchAuditLog();
    const interval = setInterval(fetchAuditLog, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleToggleModel = async () => {
    const nextModel = activeModel === 'AASIST' ? 'rawnet' : 'aasist';
    try {
      const res = await fetch(apiUrl('/api/set-model'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: nextModel }),
      });
      const data = await res.json();
      if (data.active_model) setActiveModel(data.active_model);
    } catch (e) {
      console.error('Error setting model:', e);
    }
  };

  const fetchAuditLog = () => {
    fetch(apiUrl('/api/audit-log'))
      .then((res) => res.json())
      .then((data) => setAuditEvents(data))
      .catch((err) => console.error('Error fetching audit log:', err));
  };

  // 2. Setup WebSocket Connection
  useEffect(() => {
    connectWebSocket();
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const connectWebSocket = () => {
    const wsUrl = getWebSocketUrl('/ws/audio-stream');
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setIsConnected(true);
      console.log('Audio stream WebSocket connected');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'HANDSHAKE') {
          setSessionId(data.session_id);
        } else if (data.type === 'TELEMETRY') {
          setSmoothedRisk(data.smoothed_risk);
          setInstantRisk(data.instant_risk);
          setStatus(data.status);
          setLabel(data.label);
          setColor(data.color);
          setAnomalies(data.anomalies || []);
          setForensics(data.forensics);
          setLatencyMs(data.latency_ms);
          if (data.waveform_preview) setWaveform(data.waveform_preview);
          if (data.spectral_preview) setSpectral(data.spectral_preview);

          if (data.is_frozen) {
            setIsFrozen(true);
          }
          if (data.challenge) {
            setActiveChallenge(data.challenge);
            setIsModalOpen(true);
          }
        }
      } catch (e) {
        console.error('Error parsing telemetry frame:', e);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      // Auto-reconnect after 2s
      setTimeout(connectWebSocket, 2000);
    };

    ws.onerror = (err) => {
      console.error('WebSocket encountered error:', err);
    };

    wsRef.current = ws;
  };

  // Helper to get or initialize AudioContext
  const getAudioContext = () => {
    if (!audioContextRef.current) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      audioContextRef.current = new AudioCtx({ sampleRate: 16000 });
    }
    if (audioContextRef.current.state === 'suspended') {
      audioContextRef.current.resume();
    }
    return audioContextRef.current;
  };

  // 3. Microphone Streaming
  const handleToggleMic = async () => {
    if (isMicActive) {
      stopMic();
    } else {
      await startMic();
    }
  };

  const dcBlockerRef = useRef({ prevIn: 0, prevOut: 0 });

  const startMic = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: false,
          autoGainControl: true,
        },
      });
      micStreamRef.current = stream;

      const audioCtx = getAudioContext();
      const source = audioCtx.createMediaStreamSource(stream);
      // ScriptProcessor to capture raw PCM frames
      const processor = audioCtx.createScriptProcessor(4096, 1, 1);
      micProcessorRef.current = processor;

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        const currentRate = audioCtx.sampleRate;
        let pcm16k;

        // Anti-aliasing downsampler to 16,000 Hz
        if (currentRate === 16000) {
          pcm16k = inputData;
        } else {
          const ratio = currentRate / 16000;
          const targetLen = Math.floor(inputData.length / ratio);
          pcm16k = new Float32Array(targetLen);

          // 3-tap FIR anti-aliasing smoothing before downsampling
          for (let j = 0; j < targetLen; j++) {
            const srcIdx = j * ratio;
            const idx0 = Math.floor(srcIdx);
            const idx1 = Math.min(idx0 + 1, inputData.length - 1);
            const idxPrev = Math.max(0, idx0 - 1);
            const frac = srcIdx - idx0;

            // Low-pass filtered interpolation
            const smooth0 = 0.25 * inputData[idxPrev] + 0.5 * inputData[idx0] + 0.25 * inputData[idx1];
            const smooth1 = inputData[idx1];
            pcm16k[j] = (1 - frac) * smooth0 + frac * smooth1;
          }
        }

        // DC-blocking filter (60Hz highpass cut to eliminate desk fan rumble)
        let { prevIn, prevOut } = dcBlockerRef.current;
        const filteredPcm = new Float32Array(pcm16k.length);
        for (let i = 0; i < pcm16k.length; i++) {
          const currentIn = pcm16k[i];
          const currentOut = currentIn - prevIn + 0.995 * prevOut;
          prevIn = currentIn;
          prevOut = currentOut;
          filteredPcm[i] = currentOut;
        }
        dcBlockerRef.current = { prevIn, prevOut };

        // Convert Float32 [-1.0, 1.0] to signed 16-bit PCM integer
        const int16Array = new Int16Array(filteredPcm.length);
        for (let i = 0; i < filteredPcm.length; i++) {
          const s = Math.max(-1, Math.min(1, filteredPcm[i]));
          int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        }

        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(int16Array.buffer);
        }
      };

      source.connect(processor);
      processor.connect(audioCtx.destination);
      setIsMicActive(true);
    } catch (err) {
      console.error('Error opening microphone:', err);
      alert('Microphone access was denied or is not supported. Please allow mic permissions.');
    }
  };

  const stopMic = () => {
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach((t) => t.stop());
      micStreamRef.current = null;
    }
    if (micProcessorRef.current) {
      micProcessorRef.current.disconnect();
      micProcessorRef.current = null;
    }
    setIsMicActive(false);
  };

  // 4. Controls & Prevention actions
  const handleToggleTelephony = () => {
    const nextVal = !telephonyMode;
    setTelephonyMode(nextVal);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ command: 'SET_TELEPHONY', enabled: nextVal }));
    }
  };

  const handleResetBuffer = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ command: 'RESET_BUFFER' }));
    }
    setIsFrozen(false);
    setActiveChallenge(null);
    setIsModalOpen(false);
  };

  const handleManualTriggerChallenge = async () => {
    try {
      const res = await fetch(apiUrl('/api/trigger-challenge'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId || 'SES-DEMO',
          trigger_risk: smoothedRisk,
          reason: anomalies[0] || 'Operator triggered manual forensic challenge',
        }),
      });
      const data = await res.json();
      setActiveChallenge(data);
      setIsFrozen(true);
      setIsModalOpen(true);
      fetchAuditLog();
    } catch (err) {
      console.error('Error triggering challenge:', err);
    }
  };

  const handleVerifyOtp = async (otpCode) => {
    const res = await fetch(apiUrl('/api/verify-otp'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId || activeChallenge?.session_id,
        otp_code: otpCode,
      }),
    });
    const result = await res.json();
    if (result.success) {
      setIsFrozen(false);
      setActiveChallenge(null);
    }
    fetchAuditLog();
    return result;
  };

  const handleQuarantine = async () => {
    stopMic();
    await fetch(apiUrl('/api/quarantine'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId || activeChallenge?.session_id,
        reason: 'Operator terminated and quarantined voice line due to confirmed deepfake attack',
      }),
    });
    setIsFrozen(true);
    setIsModalOpen(false);
    fetchAuditLog();
    alert('Voice line has been terminated and quarantined. Incident logged.');
  };

  return (
    <div className="min-h-screen bg-black text-zinc-100 flex flex-col font-sans">
      {/* Minimalist Monochromatic Navbar */}
      <Navbar
        isConnected={isConnected}
        isMicActive={isMicActive}
        onToggleMic={handleToggleMic}
      />

      {/* Main Operator Dashboard Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-6 space-y-6">
        {/* Top: Threat Gauge & Real-time Biometrics */}
        <div>
          <ThreatMeter
            smoothedRisk={smoothedRisk}
            instantRisk={instantRisk}
            status={status}
            label={label}
            color={color}
            isFrozen={isFrozen}
            anomalies={anomalies}
            onTriggerChallenge={handleManualTriggerChallenge}
          />
        </div>

        {/* Middle Section: Real-Time Waveform & Spectral Waterfall */}
        <SpectralWaterfall
          waveform={waveform}
          spectral={spectral}
          isSynthetic={smoothedRisk >= 80 || color === 'red'}
        />

        {/* Bottom Grid: Acoustic Forensics Cards & Forensic Audit Log */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-7">
            <AcousticForensics forensics={forensics} latencyMs={latencyMs} />
          </div>
          <div className="lg:col-span-5">
            <AuditLog events={auditEvents} />
          </div>
        </div>
      </main>

      {/* Out-of-Band Prevention Modal (pops up when threat > 80%) */}
      <PreventionModal
        isOpen={isModalOpen}
        challenge={activeChallenge}
        sessionId={sessionId}
        onVerifyOtp={handleVerifyOtp}
        onQuarantine={handleQuarantine}
        onClose={() => setIsModalOpen(false)}
      />
    </div>
  );
}
