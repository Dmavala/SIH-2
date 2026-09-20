---
title: Deepfake Voice Detector
emoji: 🎙️
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 8000
pinned: false
---

# AEGIS VOICE-SENTINEL: Real-Time Audio Deepfake Detection & In-Call Prevention

**Smart India Hackathon (SIH) Real-Time AI Audio Defense Architecture**

---

## 1. Problem & Core Attack Anatomy
Neural TTS and Voice Conversion (VC) algorithms (HiFi-GAN, MelGAN, XTTS-v2, RVC) leave subtle mathematical and physical traces that human ears overlook during voice calls:

1. **Spectral & Phase Inconsistencies**: Neural vocoders synthesize phase artificially from mel-spectrograms, producing high-frequency phase dispersion and envelope ripples in the linear upper band ($3.5\text{ kHz} - 8.0\text{ kHz}$).
2. **Acoustic & Prosodic Artifacts**: Synthetic models lack human vocal-fold micro-tremors (flat cycle-to-cycle F0 jitter $< 0.35\%$), exhibit constrained pitch variance, and miss natural respiratory micro-pauses at phrase boundaries.
3. **Acoustic Environment Disconnect**: Generative speech is synthesized in digital vacuum, lacking ambient room reverberation (RT60) and physical microphone noise floors ($-30\text{ dB}$ to $-55\text{ dB}$ in real rooms vs. $<-70\text{ dB}$ pristine digital silence).

---

## 2. End-to-End System Architecture

```
  [ Live Mic / VoIP Audio Stream ]
                 │ (16kHz PCM Audio Stream over WebSocket)
                 ▼
┌───────────────────────────────────────────────────────────┐
│              Audio Ingestion & Chunking Layer             │
│  - 2.0s sliding window buffer with 0.5s hop size          │
│  - Streaming inference dispatched every 500ms             │
└────────────────────────────┬──────────────────────────────┘
                             │
 ┌───────────────────────────┴─────────────────────────────┐
 │            AASIST / RawNet Raw Waveform Engine          │
 │  - SincNet: 70 learnable bandpass sinc filterbanks      │
 │  - Spectro-Temporal Graph Attention Networks (GAT)      │
 │  - Acoustic Forensics: Micro-Jitter, Phase Dispersion   │
 │  - Ambient Noise Floor & Respiratory Micro-Pauses       │
 └───────────────────────────┬─────────────────────────────┘
                             │
 ┌───────────────────────────┴─────────────────────────────┐
 │                Deepfake Detection Engine                │
 │  - AASIST: Spectral GAT + Temporal GAT + HS-GAL         │
 │  - RawNet2: Residual CNN with Feature Map Scaling (FMS) │
 │  - Telephony G.711 Bandpass (300Hz-3400Hz) Robustness   │
 │  - Ultra-low latency: ~14.8 ms on Apple Silicon (MPS)   │
 └───────────────────────────┬─────────────────────────────┘
                             │
 ┌───────────────────────────┴─────────────────────────────┐
 │                Prevention & Action Layer                │
 │  - Exponential Moving Average Threat Meter (0 - 100%)   │
 │  - In-Call Prevention Hook (Auto-Triggers when Risk >75%)│
 │  - Out-of-Band Challenge: Automated OTP verification    │
 │  - Live Line Quarantine & Tamper-Evident Audit Logging  │
 └───────────────────────────┬─────────────────────────────┘
                             │ (Real-time telemetry JSON)
                             ▼
┌───────────────────────────────────────────────────────────┐
│               Operator View / Live Dashboard              │
│  - Real-time Waveform Oscilloscope & Spectral Waterfall   │
│  - Dynamic Biometric Badge (Green Authentic / Red Clone)  │
│  - Call Switcher: Live Mic vs Authentic vs Deepfakes      │
│  - Out-of-Band OTP Challenge Modal & Call Quarantine      │
└───────────────────────────────────────────────────────────┘
```

---

## 3. Key Differentiators & Technical Solutions

| Challenge | Typical SIH Mistake | AEGIS Solution |
| :--- | :--- | :--- |
| **Model Architecture** | Shallow MFCC classifiers or bulky 2B-parameter models | **AASIST & RawNet2**: End-to-end raw waveform processing with 70-channel learnable SincNet and Spectro-Temporal Graph Attention. |
| **Inference Latency** | High-latency pipelines ($>500\text{ ms}$) failing real-time requirements | **Ultra-Low Latency**: AASIST averages **$\approx 14.8\text{ ms}$** and RawNet2 averages **$\approx 9.5\text{ ms}$** on Apple Silicon (MPS), well within the $<150\text{ ms}$ limit. |
| **Clean Audio Overfitting** | Fails on 8kHz/16kHz telephone audio | **Telephony Augmentation**: Built-in G.711 / AMR 300Hz-3400Hz bandpass filter and ambient noise robustness. |
| **Accent Robustness** | Semantic/phonetic models break on regional Indian accents | **Vocal-Tract Physics**: Extracts acoustic biometrics (micro-jitter, phase dispersion) rather than phonetics. |
| **Prevention** | Passive classification only | **Active In-Call Defense**: Freezes high-value call actions and forces secondary Out-of-Band OTP verification. |

---

## 4. Quick Start & Execution

### Prerequisites
- Python 3.10+ (tested with Python 3.14 on macOS ARM64)
- Node.js 18+ and npm

### 1. Launch with One Command
```bash
./start.sh
```
This runs the FastAPI backend engine and serves the modern React operator dashboard unified on **`http://localhost:8000`**.

### 2. Alternatively Run Components Separately
**Backend:**
```bash
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend (Dev Mode with Hot Reload):**
```bash
cd frontend
npm run dev
```

---

## 5. Winning Demonstration Workflow for Judges

1. **Open Dashboard**: Navigate to `http://localhost:8000`.
2. **Verify Authentic Speech (Indian Accent)**:
   - Under *Audio Ingestion & Call Simulator*, click **"🟢 Switch to Authentic Human"**.
   - Observe the dashboard:
     - Threat Meter drops to **$6.0\%$** (Solid Green: `AUTHENTIC HUMAN BIOMETRICS`).
     - Oscilloscope glows green.
     - Vocal micro-jitter reads $\approx 1.77\%$ (natural vocal fold tremor).
     - Ambient noise floor reads $-35.8\text{ dB}$ (authentic room reflection).
3. **Simulate Live Voice Clone Attack**:
   - Click **"🔴 Trigger HiFi-GAN Clone"** mid-call.
   - Within **1.5 seconds**:
     - Threat meter spikes to **$99.0\%$** (Pulsing Red: `CRITICAL_SYNTHETIC`).
     - Oscilloscope line shifts to crimson red.
     - Spectral waterfall highlights the red vocoder phase distortion in the $3.5\text{ kHz} - 8.0\text{ kHz}$ artifact zone.
     - **In-Call Defense Hook activates automatically**: Line freezes and the **Out-of-Band OTP Challenge Modal** pops up.
4. **Resolve Challenge**:
   - Use the auto-fill or enter the generated 6-digit OTP to authenticate via the secondary channel.
   - Click **"Verify & Unlock Action"** to unfreeze the transaction, or click **"Terminate Line"** to quarantine the call.
5. **Test Live Microphone**:
   - Click **"Start Live Mic Stream"** and speak directly into your microphone to inspect live biometrics in real time.
