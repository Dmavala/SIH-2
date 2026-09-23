/**
 * useAegisStream — encapsulates ALL real-time streaming logic:
 *   WebSocket connection + heartbeat + auto-reconnect
 *   Telemetry state (risk, status, forensics, waveform, spectral)
 *   Threat-alert latching (challenge modal trigger)
 *   Live microphone capture (AudioWorklet + ScriptProcessor fallback)
 *   16 kHz resampling & chunked PCM streaming
 *
 * Extracted from App.jsx so the UI layer stays declarative.
 *
 * Threat-response lifecycle (important):
 *   When a sustained attack is detected the hook pauses microphone capture
 *   (mic stays armed, session stays open), raises the advisory modal, and
 *   resets backend/client buffers. Closing the modal calls resumeAfterThreat()
 *   which clears the latch, resets telemetry, and restarts the mic.
 *   Two prior bugs made the UI die after the first popup:
 *     1) the mic was hard-stopped on alert and never restarted;
 *     2) the threat pause initially called stopMic(), whose "intentional stop"
 *        flag-wipe erased the resume intent (wasMicActiveRef) before the
 *        modal even closed — fixed by a dedicated teardownMicCapture() pause.
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
    return true; // Keep alive indefinitely across any silence or pauses
  }
}
registerProcessor('continuous-audio-processor', ContinuousAudioProcessor);
`;

export default function useAegisStream({ onThreatDetected, onMicError }) {
  // Telemetry state
  const [isConnected, setIsConnected] = useState(false);
  const [sessionId, setSessionId] = useState('');
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
  const [isFrozen, setIsFrozen] = useState(false);
  const [activeChallenge, setActiveChallenge] = useState(null);
  const [telephonyMode, setTelephonyMode] = useState(false);
  const [isMicActive, setIsMicActive] = useState(false);

  // Refs
  const wsRef = useRef(null);
  const pingTimerRef = useRef(null);
  const hasAlertedRef = useRef(false);
  const isResettingRef = useRef(false);
  const audioContextRef = useRef(null);
  const micStreamRef = useRef(null);
  const micProcessorRef = useRef(null);
  const workletRegisteredRef = useRef(false);
  const audioStreamBufferRef = useRef(new Float32Array(0));
  const stopMicRef = useRef(null);
  const teardownMicCaptureRef = useRef(null); // pause mic WITHOUT clearing resume intent
  const wasMicActiveRef = useRef(false); // mic state before threat pause
  const isMicActiveRef = useRef(false); // live mic state for WS closures
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
          setSmoothedRisk(0.0);
          setInstantRisk(0.0);
          setStatus('IDLE_SILENCE');
          setLabel('MONITORING - AWAITING SPEECH');
          setColor('slate');
          setAnomalies([]);
          setForensics(null);
          setWaveform([]);
          setSpectral([]);
          setIsFrozen(false);
          setActiveChallenge(null);
          // Allow 800ms microphone stabilization window before re-arming alert trigger
          setTimeout(() => {
            hasAlertedRef.current = false;
          }, 800);
        } else if (data.type === 'TELEMETRY') {
          // Drop stale frames arriving while resetting or before state settles
          if (isResettingRef.current) return;

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

          if (data.is_frozen !== undefined) setIsFrozen(Boolean(data.is_frozen));

          // Only genuine verified synthetic voice attacks trigger the modal & pause mic
          const isFishy = Boolean(
            (data.challenge && data.smoothed_risk >= 70.0) ||
            (data.status === 'CRITICAL_SYNTHETIC' && data.smoothed_risk >= 75.0)
          );

          if (isFishy && !hasAlertedRef.current && !isResettingRef.current) {
            hasAlertedRef.current = true;
            isResettingRef.current = true;
            if (data.challenge) setActiveChallenge(data.challenge);

            // 1. Trigger the safety advisory popup immediately with true detection data
            if (onThreatDetectedRef.current) onThreatDetectedRef.current(data);

            // 2. PAUSE (not stop) mic hardware capture — keeps the mic armed so
            //    closing the advisory can resume analysis without a fresh
            //    getUserMedia prompt. wasMicActiveRef remembers the prior state.
            //    CRITICAL: use teardownMicCapture (NOT stopMic) here — stopMic
            //    marks the stop as "intentional" and would wipe wasMicActiveRef,
            //    so resumeAfterThreat could never know the mic must restart
            //    (this was the root cause of the "dead after first popup" bug).
            wasMicActiveRef.current = isMicActiveRef.current;
            if (teardownMicCaptureRef.current) teardownMicCaptureRef.current();

            // 3. Immediately reset backend audio buffer and threat aggregator
            sendCommand('RESET_BUFFER');

            // 4. Immediately clear client audio buffers and visualizations
            audioStreamBufferRef.current = new Float32Array(0);
            setWaveform([]);
            setSpectral([]);
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
    if (!audioContextRef.current) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      const ctx = new AudioCtx();
      ctx.onstatechange = () => {
        if (ctx.state === 'suspended') ctx.resume().catch(() => {});
      };
      audioContextRef.current = ctx;
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
    // Immediate visual feedback on client oscilloscope
    if (pcm16k.length > 0) {
      const step = Math.max(1, Math.floor(pcm16k.length / 128));
      const preview = [];
      for (let i = 0; i < pcm16k.length && preview.length < 128; i += step) {
        preview.push(pcm16k[i]);
      }
      setWaveform(preview);
    }

    audioStreamBufferRef.current = combined.subarray(offset);
  }, [sendAudioChunk]);

  /**
   * Tear down mic capture nodes WITHOUT touching resume-intent state.
   * Used by both stopMic (intentional stop) and the threat pause (temporary).
   */
  const teardownMicCapture = useCallback(() => {
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach((t) => {
        t.stop();
        t.enabled = false;
      });
      micStreamRef.current = null;
    }
    if (micProcessorRef.current) {
      micProcessorRef.current.disconnect();
      micProcessorRef.current = null;
    }
    window.__activeMicProcessor = null;
    audioStreamBufferRef.current = new Float32Array(0);
    setIsMicActive(false);
  }, []);
  teardownMicCaptureRef.current = teardownMicCapture;

  const stopMic = useCallback(() => {
    teardownMicCapture();
    wasMicActiveRef.current = false; // intentional stop — do not auto-resume later
  }, [teardownMicCapture]);
  stopMicRef.current = stopMic;

  /**
   * Failsafe: if the backend RESET_ACK is lost (WS reconnect race), the latch
   * must never wedge — telemetry would be dropped forever and the alert
   * trigger would stay disarmed. RESET_ACK clears both earlier when it does
   * arrive; this timer is pure insurance.
   */
  const armLatchFailsafe = useCallback(() => {
    setTimeout(() => {
      isResettingRef.current = false;
      hasAlertedRef.current = false;
    }, 1500);
  }, []);

  const handleResetBuffer = useCallback(() => {
    isResettingRef.current = true;
    sendCommand('RESET_BUFFER');
    armLatchFailsafe();
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
    if (stopMicRef.current) stopMicRef.current();
  }, [sendCommand]);

  const startMic = useCallback(async () => {
    try {
      // 1. Engage reset latch so any residual in-flight frames are safely dropped
      isResettingRef.current = true;
      hasAlertedRef.current = true;

      // 2. Command backend to flush any residue from prior sessions
      sendCommand('RESET_BUFFER');
      armLatchFailsafe();

      // 3. Reset frontend telemetry state to fresh monitoring baseline
      setSmoothedRisk(0.0);
      setInstantRisk(0.0);
      setStatus('IDLE_SILENCE');
      setLabel('MONITORING - AWAITING SPEECH');
      setColor('slate');
      setAnomalies([]);
      setForensics(null);
      setWaveform([]);
      setSpectral([]);
      setIsFrozen(false);
      setActiveChallenge(null);
      audioStreamBufferRef.current = new Float32Array(0);

      // 4. Request microphone hardware stream with browser noise suppression enabled
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
    } catch (err) {
      console.error('Error opening microphone:', err);
      if (onMicErrorRef.current) onMicErrorRef.current(err);
    }
  }, [getAudioContext, sendAudioData, sendCommand, armLatchFailsafe]);

  /**
   * Resume realtime analysis after a threat advisory is dismissed.
   * Fixes the "one popup, then dead" bug: clears the reset latch, resets
   * telemetry, restarts mic capture, and re-arms the threat trigger.
   */
  const resumeAfterThreat = useCallback(async () => {
    // NOTE: isResettingRef stays TRUE until RESET_ACK arrives — pre-reset
    // telemetry frames (FIFO) are then dropped, so a stale CRITICAL frame can
    // never re-trigger the modal. hasAlertedRef is re-armed by RESET_ACK's
    // 800ms stabilization timer (and by the failsafe if the ACK is lost).

    // 2. Flush backend buffers + aggregator and get a clean RESET_ACK baseline
    sendCommand('RESET_BUFFER');
    armLatchFailsafe();

    // 3. Restart mic if it was active before the threat pause (fresh capture,
    //    no new permission prompt since context + worklet are still registered).
    //    Read the live ref, not the state snapshot — after the pause teardown,
    //    the isMicActive STATE is false but wasMicActiveRef holds the truth.
    if (wasMicActiveRef.current || isMicActiveRef.current) {
      await startMic();
    }
  }, [sendCommand, startMic, armLatchFailsafe]);

  const handleToggleMic = useCallback(() => {
    if (isMicActive) {
      stopMic();
      handleResetBuffer();
    } else {
      startMic();
    }
  }, [isMicActive, stopMic, handleResetBuffer, startMic]);

  // ---------------- Session controls ----------------
  const handleToggleTelephony = useCallback(() => {
    setTelephonyMode((prev) => {
      const next = !prev;
      sendCommand('SET_TELEPHONY', { enabled: next });
      return next;
    });
  }, [sendCommand]);

  return {
    // connection & telemetry
    isConnected, sessionId, smoothedRisk, instantRisk, status, label, color,
    anomalies, forensics, latencyMs, waveform, spectral,
    // prevention
    isFrozen, activeChallenge, setActiveChallenge,
    // mic & controls
    isMicActive, handleToggleMic, stopMic, stopMicRef, startMic, resumeAfterThreat,
    telephonyMode, handleToggleTelephony, handleResetBuffer,
    wsRef,
  };
}
