/**
 * useAegisStream — encapsulates ALL real-time streaming logic:
 *   WebSocket connection + heartbeat + auto-reconnect
 *   Telemetry state (risk, status, forensics, waveform, spectral)
 *   Threat-alert latching (challenge modal trigger)
 *   Live microphone capture with pristine AudioContext lifecycle
 *   Pre-loaded benchmark audio playback & streaming feeder
 *   16 kHz resampling & chunked PCM streaming
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { apiUrl, getWebSocketUrl } from '../config';

const AUDIO_WORKLET_CODE = `
class ContinuousAudioProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.buffer = new Float32Array(4096);
    this.offset = 0;
  }
  process(inputs, outputs, parameters) {
    const input = inputs[0];
    const output = outputs[0];
    if (input && input.length > 0) {
      const channelData = input[0];
      if (channelData && channelData.length > 0) {
        if (output && output.length > 0) {
          output[0].set(channelData);
        }
        for (let i = 0; i < channelData.length; i++) {
          this.buffer[this.offset++] = channelData[i];
          if (this.offset >= this.buffer.length) {
            this.port.postMessage(this.buffer);
            this.buffer = new Float32Array(4096);
            this.offset = 0;
          }
        }
      }
    }
    return true;
  }
}
registerProcessor('continuous-audio-processor', ContinuousAudioProcessor);
`;

export default function useAegisStream({ onThreatDetected, onMicError }) {
  // Telemetry state
  const [isConnected, setIsConnected] = useState(false);
  const [sessionId, setSessionId] = useState('');
  const [smoothedRisk, setSmoothedRisk] = useState(0.0);
  const [instantRisk, setInstantRisk] = useState(0.0);
  const [status, setStatus] = useState('IDLE_SILENCE');
  const [label, setLabel] = useState('MONITORING - AWAITING SPEECH');
  const [color, setColor] = useState('slate');
  const [anomalies, setAnomalies] = useState([]);
  const [forensics, setForensics] = useState(null);
  const [latencyMs, setLatencyMs] = useState(21.4);
  const [waveform, setWaveform] = useState([]);
  const [spectral, setSpectral] = useState([]);
  const [isFrozen, setIsFrozen] = useState(false);
  const [activeChallenge, setActiveChallenge] = useState(null);
  const [telephonyMode, setTelephonyMode] = useState(false);
  const [isMicActive, setIsMicActive] = useState(false);
  const [isPlayingSample, setIsPlayingSample] = useState(false);
  const [currentSampleId, setCurrentSampleId] = useState(null);

  // Refs
  const wsRef = useRef(null);
  const pingTimerRef = useRef(null);
  const hasAlertedRef = useRef(false);
  const isResettingRef = useRef(false);
  const audioContextRef = useRef(null);
  const micStreamRef = useRef(null);
  const micSourceRef = useRef(null);
  const micProcessorRef = useRef(null);
  const workletRegisteredRef = useRef(false);
  const audioStreamBufferRef = useRef(new Float32Array(0));
  const sampleIntervalRef = useRef(null);

  const stopMicRef = useRef(null);
  const wasMicActiveRef = useRef(false);
  const isMicActiveRef = useRef(false);
  isMicActiveRef.current = isMicActive;
  const onThreatDetectedRef = useRef(onThreatDetected);
  onThreatDetectedRef.current = onThreatDetected;
  const onMicErrorRef = useRef(onMicError);
  onMicErrorRef.current = onMicError;

  const connectWebSocket = useCallback(() => {
    if (pingTimerRef.current) {
      clearInterval(pingTimerRef.current);
      pingTimerRef.current = null;
    }

    try {
      const ws = new WebSocket(getWebSocketUrl('/ws/audio-stream'));

      ws.onopen = () => {
        setIsConnected(true);
        pingTimerRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ command: 'PING' }));
          }
        }, 5000);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'PONG') return;
          if (data.type === 'HANDSHAKE') {
            setSessionId(data.session_id);
          } else if (data.type === 'RESET_ACK') {
            isResettingRef.current = false;
            hasAlertedRef.current = false;
            setIsFrozen(false);
            setSmoothedRisk(0.0);
            setInstantRisk(0.0);
            setStatus('IDLE_SILENCE');
            setLabel('MONITORING - AWAITING SPEECH');
            setColor('slate');
            setAnomalies([]);
            setForensics(null);
            setWaveform([]);
            setSpectral([]);
            setActiveChallenge(null);
          } else if (data.type === 'TELEMETRY') {
            if (isResettingRef.current) return;

            setSmoothedRisk(data.smoothed_risk);
            setInstantRisk(data.instant_risk);
            setStatus(data.status);
            setLabel(data.label);
            setColor(data.color);
            setAnomalies(data.anomalies || []);
            setForensics(data.forensics);
            setLatencyMs(data.latency_ms);
            if (data.waveform_preview && data.waveform_preview.length > 0) {
              setWaveform(data.waveform_preview);
            }
            if (data.spectral_preview && data.spectral_preview.length > 0) {
              setSpectral(data.spectral_preview);
            }

            if (data.is_frozen !== undefined) setIsFrozen(Boolean(data.is_frozen));

            // Verified synthetic voice attacks trigger advisory
            const isFishy = Boolean(
              (data.challenge && data.smoothed_risk >= 70.0) ||
              (data.status === 'CRITICAL_SYNTHETIC' && data.smoothed_risk >= 75.0)
            );

            if (isFishy && !hasAlertedRef.current && !isResettingRef.current) {
              hasAlertedRef.current = true;
              if (data.challenge) setActiveChallenge(data.challenge);

              if (onThreatDetectedRef.current) onThreatDetectedRef.current(data);

              wasMicActiveRef.current = isMicActiveRef.current;
              if (stopMicRef.current) stopMicRef.current(false);

              sendCommand('RESET_BUFFER');
              audioStreamBufferRef.current = new Float32Array(0);
              setIsFrozen(true);
            }
          }
        } catch (e) {
          console.error('Error parsing telemetry frame:', e);
        }
      };

      ws.onclose = () => {
        if (pingTimerRef.current) {
          clearInterval(pingTimerRef.current);
          pingTimerRef.current = null;
        }
        setIsConnected(false);
        setTimeout(connectWebSocket, 2000);
      };

      ws.onerror = (err) => console.error('WebSocket encountered error:', err);
      wsRef.current = ws;
    } catch (e) {
      console.error('WebSocket connection initialization error:', e);
      setTimeout(connectWebSocket, 3000);
    }
  }, []);

  useEffect(() => {
    connectWebSocket();
    return () => {
      if (pingTimerRef.current) clearInterval(pingTimerRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connectWebSocket]);

  const sendCommand = useCallback((command, extra = {}) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ command, ...extra }));
    }
  }, []);

  const sendAudioChunk = useCallback((pcm16k) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(pcm16k);
    }
  }, []);

  // ---------------- Microphone capture ----------------
  const getAudioContext = useCallback(async () => {
    if (!audioContextRef.current || audioContextRef.current.state === 'closed') {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      const ctx = new AudioCtx();
      ctx.onstatechange = () => {
        if (ctx.state === 'suspended') ctx.resume().catch(() => {});
      };
      audioContextRef.current = ctx;
      workletRegisteredRef.current = false;
    }
    const ctx = audioContextRef.current;
    if (ctx.state === 'suspended') await ctx.resume().catch(() => {});

    if (ctx.audioWorklet && !workletRegisteredRef.current) {
      try {
        const blob = new Blob([AUDIO_WORKLET_CODE], { type: 'application/javascript' });
        const url = URL.createObjectURL(blob);
        await ctx.audioWorklet.addModule(url);
        URL.revokeObjectURL(url);
        workletRegisteredRef.current = true;
      } catch (err) {
        console.warn('AudioWorklet registration error, using ScriptProcessor fallback:', err);
      }
    }
    return ctx;
  }, []);

  const sendAudioData = useCallback((inputData, currentRate) => {
    if (!inputData || inputData.length === 0) return;

    let pcm16k;
    if (currentRate === 16000) {
      pcm16k = inputData;
    } else {
      const ratio = currentRate / 16000;
      const targetLen = Math.floor(inputData.length / ratio);
      pcm16k = new Float32Array(targetLen);
      for (let j = 0; j < targetLen; j++) {
        const srcIdx = j * ratio;
        const idx0 = Math.floor(srcIdx);
        const idx1 = Math.min(idx0 + 1, inputData.length - 1);
        const frac = srcIdx - idx0;
        pcm16k[j] = (1 - frac) * inputData[idx0] + frac * inputData[idx1];
      }
    }

    const prevBuf = audioStreamBufferRef.current;
    const combined = new Float32Array(prevBuf.length + pcm16k.length);
    combined.set(prevBuf);
    combined.set(pcm16k, prevBuf.length);

    const CHUNK_SIZE = 2048;
    let offset = 0;
    while (combined.length - offset >= CHUNK_SIZE) {
      const chunk = combined.subarray(offset, offset + CHUNK_SIZE);
      const int16Array = new Int16Array(CHUNK_SIZE);
      for (let i = 0; i < CHUNK_SIZE; i++) {
        const s = Math.max(-1, Math.min(1, chunk[i]));
        int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
      }
      sendAudioChunk(int16Array.buffer);
      offset += CHUNK_SIZE;
    }

    if (pcm16k.length > 0) {
      const step = Math.max(1, Math.floor(pcm16k.length / 64));
      const preview = [];
      for (let i = 0; i < pcm16k.length && preview.length < 64; i += step) {
        preview.push(pcm16k[i]);
      }
      setWaveform(preview);
    }

    audioStreamBufferRef.current = combined.subarray(offset);
  }, [sendAudioChunk]);

  /**
   * Complete clean teardown of mic hardware and audio context nodes.
   * Completely avoids Chrome/macOS dead hardware pump lockups on repeated start/stops.
   */
  const teardownMicCapture = useCallback(async (intentional = true) => {
    if (micStreamRef.current) {
      try {
        micStreamRef.current.getTracks().forEach((t) => {
          t.stop();
          t.enabled = false;
        });
      } catch (e) {}
      micStreamRef.current = null;
    }

    if (micSourceRef.current) {
      try {
        micSourceRef.current.disconnect();
      } catch (e) {}
      micSourceRef.current = null;
    }

    if (micProcessorRef.current) {
      try {
        micProcessorRef.current.disconnect();
      } catch (e) {}
      micProcessorRef.current = null;
    }

    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      try {
        await audioContextRef.current.close();
      } catch (e) {}
      audioContextRef.current = null;
      workletRegisteredRef.current = false;
    }

    window.__activeMicProcessor = null;
    audioStreamBufferRef.current = new Float32Array(0);
    setIsMicActive(false);
    if (intentional) {
      wasMicActiveRef.current = false;
    }
  }, []);

  const stopMic = useCallback((intentional = true) => {
    teardownMicCapture(intentional);
  }, [teardownMicCapture]);
  stopMicRef.current = stopMic;

  const handleResetBuffer = useCallback(() => {
    isResettingRef.current = false;
    hasAlertedRef.current = false;
    setIsFrozen(false);
    setActiveChallenge(null);
    setSmoothedRisk(0.0);
    setInstantRisk(0.0);
    setStatus('IDLE_SILENCE');
    setLabel('MONITORING - AWAITING SPEECH');
    setColor('slate');
    setAnomalies([]);
    setForensics(null);
    setWaveform([]);
    setSpectral([]);
    audioStreamBufferRef.current = new Float32Array(0);
    sendCommand('RESET_BUFFER');
  }, [sendCommand]);

  const startMic = useCallback(async () => {
    try {
      // 1. Flush any prior state and unfreeze
      handleResetBuffer();

      // 2. Request fresh microphone hardware stream
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      micStreamRef.current = stream;

      const audioCtx = await getAudioContext();
      if (audioCtx.state === 'suspended') {
        await audioCtx.resume().catch(() => {});
      }
      const source = audioCtx.createMediaStreamSource(stream);
      micSourceRef.current = source;

      if (workletRegisteredRef.current) {
        const workletNode = new AudioWorkletNode(audioCtx, 'continuous-audio-processor');
        micProcessorRef.current = workletNode;
        workletNode.port.onmessage = (e) => sendAudioData(e.data, audioCtx.sampleRate);
        const silentGain = audioCtx.createGain();
        silentGain.gain.value = 0.0;
        source.connect(workletNode);
        workletNode.connect(silentGain);
        silentGain.connect(audioCtx.destination);
      } else {
        const processor = audioCtx.createScriptProcessor(4096, 1, 1);
        micProcessorRef.current = processor;
        window.__activeMicProcessor = processor;
        processor.onaudioprocess = (e) => {
          const inputData = e.inputBuffer.getChannelData(0);
          e.outputBuffer.getChannelData(0).fill(0);
          sendAudioData(inputData, audioCtx.sampleRate);
        };
        const silentGain = audioCtx.createGain();
        silentGain.gain.value = 0.0;
        source.connect(processor);
        processor.connect(silentGain);
        silentGain.connect(audioCtx.destination);
      }

      setIsMicActive(true);
      isResettingRef.current = false;
      hasAlertedRef.current = false;
    } catch (err) {
      console.error('Error opening microphone:', err);
      if (onMicErrorRef.current) onMicErrorRef.current(err);
      teardownMicCapture(true);
    }
  }, [getAudioContext, sendAudioData, handleResetBuffer, teardownMicCapture]);

  /**
   * Resume realtime analysis after a threat advisory is dismissed.
   */
  const resumeAfterThreat = useCallback(async () => {
    handleResetBuffer();
    if (wasMicActiveRef.current) {
      await startMic();
    }
  }, [handleResetBuffer, startMic]);

  const handleToggleMic = useCallback(() => {
    if (isMicActive) {
      stopMic(true);
      handleResetBuffer();
    } else {
      if (isPlayingSample) stopSample();
      startMic();
    }
  }, [isMicActive, stopMic, handleResetBuffer, startMic, isPlayingSample]);

  // ---------------- Sample Playback & Benchmark Feeder ----------------
  const stopSample = useCallback(() => {
    if (sampleIntervalRef.current) {
      clearInterval(sampleIntervalRef.current);
      sampleIntervalRef.current = null;
    }
    setIsPlayingSample(false);
    setCurrentSampleId(null);
    audioStreamBufferRef.current = new Float32Array(0);
    setWaveform([]);
  }, []);

  const playSample = useCallback(async (sample) => {
    stopMic(true);
    stopSample();
    handleResetBuffer();

    const sampleId = typeof sample === 'string' ? sample : sample.id;
    const filename = typeof sample === 'object' && sample.filename ? sample.filename : `${sampleId}.wav`;
    const url = apiUrl(`/api/audio/${filename}`);

    setIsPlayingSample(true);
    setCurrentSampleId(sampleId);

    try {
      const resp = await fetch(url);
      if (!resp.ok) {
        throw new Error(`Failed to load audio sample ${filename} (HTTP ${resp.status})`);
      }
      const arrayBuffer = await resp.arrayBuffer();

      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      const decodeCtx = new AudioCtx();
      const decodedBuffer = await decodeCtx.decodeAudioData(arrayBuffer);
      await decodeCtx.close();

      const rawData = decodedBuffer.getChannelData(0);
      const srcRate = decodedBuffer.sampleRate;

      // Resample to 16,000 Hz for the detection pipeline
      let pcm16k;
      if (srcRate === 16000) {
        pcm16k = rawData;
      } else {
        const ratio = srcRate / 16000;
        const targetLen = Math.floor(rawData.length / ratio);
        pcm16k = new Float32Array(targetLen);
        for (let j = 0; j < targetLen; j++) {
          const srcIdx = j * ratio;
          const idx0 = Math.floor(srcIdx);
          const idx1 = Math.min(idx0 + 1, rawData.length - 1);
          const frac = srcIdx - idx0;
          pcm16k[j] = (1 - frac) * rawData[idx0] + frac * rawData[idx1];
        }
      }

      // Stream 2048-sample chunks (~128ms) into WebSocket pipeline in real-time
      const CHUNK_SIZE = 2048;
      let offset = 0;
      sampleIntervalRef.current = setInterval(() => {
        if (offset >= pcm16k.length) {
          stopSample();
          return;
        }
        const slice = pcm16k.subarray(offset, Math.min(pcm16k.length, offset + CHUNK_SIZE));
        const int16Array = new Int16Array(slice.length);
        for (let i = 0; i < slice.length; i++) {
          const s = Math.max(-1, Math.min(1, slice[i]));
          int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        }
        sendAudioChunk(int16Array.buffer);

        // Feed waveform preview
        const step = Math.max(1, Math.floor(slice.length / 64));
        const preview = [];
        for (let i = 0; i < slice.length && preview.length < 64; i += step) {
          preview.push(slice[i]);
        }
        setWaveform(preview);

        offset += CHUNK_SIZE;
      }, 128);
    } catch (err) {
      console.error('Error playing sample:', err);
      stopSample();
    }
  }, [stopMic, stopSample, handleResetBuffer, sendAudioChunk]);

  // ---------------- Session controls ----------------
  const handleToggleTelephony = useCallback(() => {
    setTelephonyMode((prev) => {
      const next = !prev;
      sendCommand('SET_TELEPHONY', { enabled: next });
      return next;
    });
  }, [sendCommand]);

  return {
    isConnected, sessionId, smoothedRisk, instantRisk, status, label, color,
    anomalies, forensics, latencyMs, waveform, spectral,
    isFrozen, activeChallenge, setActiveChallenge,
    isMicActive, handleToggleMic, stopMic, startMic, resumeAfterThreat,
    isPlayingSample, currentSampleId, playSample, stopSample,
    telephonyMode, handleToggleTelephony, handleResetBuffer,
    wsRef,
  };
}
