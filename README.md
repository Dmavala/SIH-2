---
title: Deepfake Voice Detector
emoji: 🎙️
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 8000
pinned: false
---

# AEGIS VOICE-SENTINEL: Real-Time Audio Deepfake Detection & In-Call Defense
## National AI Audio Anti-Spoofing & Legal Forensic Platform for Government of India (MHA / I4C / DoT)

**Smart India Hackathon (SIH) — National Cybersecurity & Telephony Defense Architecture**

> [!IMPORTANT]
> **SIH Grand Finale Deliverables**:
> - Complete Presentation Script, Defense Strategy & Jury Q&A Matrix: [`SIH_WINNING_PITCH_AND_ARCHITECTURE.md`](file:///c:/Users/CodeX/Desktop/SIH-2/SIH_WINNING_PITCH_AND_ARCHITECTURE.md)
> - Court-Admissible Electronic Evidence Engine: **Section 63 of Bharatiya Sakshya Adhiniyam (BSA), 2023**

---

## 1. Problem & Indian Threat Landscape
In India, AI voice cloning has triggered an unprecedented surge in high-impact cybercrimes:
1. **"Digital Arrest" Scams**: Cyber syndicates impersonating CBI, State Police, and Customs officers with synthetic voices to extort citizens.
2. **Family Emergency / Ransom Clones**: High-fidelity clones synthesized from 3-second social media clips to stage fake accidents and abductions.
3. **Banking KYC Expiry Phishing**: High-pressure automated voice calls claiming immediate account/debit card suspension.
4. **Physical Vocoder Footprints**: Neural vocoders (HiFi-GAN, XTTS, ElevenLabs, RVC) leave unnatural mathematical signatures:
   - Severe high-frequency phase dispersion ($3.5\text{ kHz} - 8.0\text{ kHz}$).
   - Constrained pitch variance and flat vocal micro-jitter ($<0.35\%$).
   - Pristine digital background vacuum ($<-70\text{ dB}$ vs $-35\text{ dB}$ to $-55\text{ dB}$ in authentic phone calls).

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
- Python 3.10+
- Node.js 18+ and npm

### 1. Configure (all values env-driven — nothing hardcoded)
```bash
cp .env.example .env   # defaults are fine for local dev
```
Every threshold (risk levels, OTP policy, CORS, auth, rate limits, DB path,
consensus engine weights) is set via environment variables. See
**docs/DEPLOYMENT.md** for the full government-deployment configuration and the
honest readiness assessment.

### 2. Launch with One Command
```bash
./start.sh
```
This runs the FastAPI backend engine and serves the modern React operator dashboard unified on **`http://localhost:8000`**.

### 3. Alternatively Run Components Separately
**Backend:**
```bash
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

**Frontend (Dev Mode with Hot Reload):**
```bash
cd frontend
npm run dev
```

### 4. Run the Test Suite
```bash
python -m unittest discover -s tests   # 54 tests: security, evidence chain, consensus, API
```

### 5. Retrain on Real Data (recommended before any deployment claim)
```bash
python -m backend.training.train --data-dir large_benchmark_data,test_realworld_samples,scam_call_data --epochs 30
python scripts/build_real_demo_samples.py   # rebuild REAL demo audio
python scripts/run_full_evaluation.py       # honest benchmark -> full_benchmark_report.json
python scripts/load_test.py                 # throughput/latency (server must be running)
cat backend/models/training_meta.json       # honest training record (quote this in evaluations)
```

**Current verified behaviour** (167 real in-repo clips, `full_benchmark_report.json`):
0 deepfakes pass as authentic, 1/167 real clips flagged (0.6% FPR), 91 crisp
verdicts (90 correct), 76 escalated to human review. Stream-frame latency
6.5 ms mean / 7.5 ms P95 on CPU.

### Demo Samples Are Real Recordings
The bundled demo WAVs are **real** human speech, real reported scam calls, and
real output from ElevenLabs / Play.ht / HiFi-GAN (built by
`scripts/build_real_demo_samples.py` from the in-repo corpora). The original
procedurally-synthesized demo files were retired — they made "authentic human"
demos literally synthetic.

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
