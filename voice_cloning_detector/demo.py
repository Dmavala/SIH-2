"""
Interactive Streamlit Web Application for AI-Powered Voice Cloning & Deepfake Speech Detection.

Features:
- File upload (.wav, .mp3, .flac, .ogg, .m4a) and live microphone recording
- Preset sample loader for real human speech and various cloning tools (RVC, XTTS, ElevenLabs, Bark)
- Color-coded decision badge (REAL vs FAKE) with confidence gauge
- 3-Branch Ensemble Breakdown with weighted contributions
- Visual Explanation Suite:
  - Magnitude spectrogram vs Instantaneous Frequency Deviation (Phase) heatmap
  - Biological acoustic indicators (breathing, silence dynamics, pitch jitter & shimmer)
  - Multi-chunk sliding window temporal prediction timeline
"""

import os
import sys

# Ensure repository root directory is on sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import io
import time
import tempfile
import numpy as np
import soundfile as sf
import matplotlib.pyplot as plt
import streamlit as st

from voice_cloning_detector.config import (
    CHECKPOINTS_DIR, REAL_DIR, FAKE_DIR, SAMPLE_RATE,
    DECISION_THRESHOLD, DEFAULT_BRANCH_WEIGHTS
)
from voice_cloning_detector.dataset import load_and_standardize_audio
from voice_cloning_detector.inference import VoiceCloningInferenceEngine

# Page configuration
st.set_page_config(
    page_title="AI Voice Cloning & Deepfake Speech Detector",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS styling for premium look
st.markdown("""
<style>
    .metric-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .badge-fake {
        background: linear-gradient(135deg, #ef4444 0%, #b91c1c 100%);
        color: white;
        padding: 12px 24px;
        border-radius: 8px;
        font-size: 28px;
        font-weight: 800;
        text-align: center;
        letter-spacing: 1px;
    }
    .badge-real {
        background: linear-gradient(135deg, #10b981 0%, #047857 100%);
        color: white;
        padding: 12px 24px;
        border-radius: 8px;
        font-size: 28px;
        font-weight: 800;
        text-align: center;
        letter-spacing: 1px;
    }
    .sub-badge {
        font-size: 14px;
        color: #64748b;
        margin-top: 4px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_engine():
    """Caches the inference engine so model weights aren't reloaded every interaction."""
    ckpt = os.path.join(CHECKPOINTS_DIR, "best_model.pt")
    ckpt_to_use = ckpt if os.path.exists(ckpt) else None
    return VoiceCloningInferenceEngine(checkpoint_path=ckpt_to_use)


engine = get_engine()

# Sidebar
st.sidebar.title("🎙️ Audio Controls")
st.sidebar.markdown("State-of-the-Art 3-Branch Deepfake Audio Detector")

input_mode = st.sidebar.radio(
    "Choose Audio Source:",
    [
        "Upload Audio File",
        "Record Microphone",
        "Benchmark Sample Library",
        "🔴 Live Real-Time Stream Simulation"
    ]
)

audio_bytes = None
audio_filename = "sample.wav"

if input_mode == "🔴 Live Real-Time Stream Simulation":
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔴 Real-Time Stream Settings")
    stream_choice = st.sidebar.selectbox(
        "Select Stream Feed:",
        ["Live Transition (Human -> AI Clone)", "Continuous Authentic Human", "Continuous AI Cloned Voice"]
    )
    update_speed = st.sidebar.slider("Chunk Interval (sec):", min_value=0.2, max_value=1.0, value=0.5, step=0.1)

elif input_mode == "Upload Audio File":
    uploaded_file = st.sidebar.file_uploader(
        "Upload audio clip (.wav, .mp3, .flac, .ogg, .m4a)",
        type=["wav", "mp3", "flac", "ogg", "m4a"]
    )
    if uploaded_file is not None:
        audio_bytes = uploaded_file.read()
        audio_filename = uploaded_file.name

elif input_mode == "Record Microphone":
    mic_audio = st.sidebar.audio_input("Record your voice (at least 3-4 seconds):")
    if mic_audio is not None:
        audio_bytes = mic_audio.read()
        audio_filename = "mic_recording.wav"

else:  # Benchmark Sample Library
    sample_type = st.sidebar.selectbox("Category:", ["Authentic Human Speech", "AI Voice Clone"])
    target_dir = REAL_DIR if sample_type == "Authentic Human Speech" else FAKE_DIR
    
    if os.path.exists(target_dir):
        available_files = [f for f in os.listdir(target_dir) if f.endswith(".wav")]
        if available_files:
            selected_file = st.sidebar.selectbox("Select Sample:", sorted(available_files))
            sample_path = os.path.join(target_dir, selected_file)
            with open(sample_path, "rb") as f:
                audio_bytes = f.read()
            audio_filename = selected_file
        else:
            st.sidebar.warning(f"No samples found in {target_dir}. Generate dataset first.")
    else:
        st.sidebar.warning("Data directory not found. Please run generate_fake_data.py first.")

# Main Page Header
st.title("🛡️ AI-Powered Voice Cloning & Deepfake Speech Detector")
st.caption("3-Branch Ensemble: Self-Supervised Wav2Vec2 + Dual-Channel Phase ResNet-18 + Temporal Biological Artifacts")

if input_mode == "🔴 Live Real-Time Stream Simulation":
    st.subheader(f"🔴 Live Streaming Monitor: `{stream_choice}`")
    st.caption("Sliding 4.0-second window updated every 500ms in real time. Simulates an active audio stream (VoIP, call center, or live mic).")
    
    start_btn = st.button("▶️ Start Live Stream Analysis", type="primary")
    if start_btn:
        from voice_cloning_detector.realtime_stream import RealTimeAudioStreamDetector
        from voice_cloning_detector.dataset import load_and_standardize_audio
        
        rt_detector = RealTimeAudioStreamDetector()
        
        # Determine sequence of audio
        if stream_choice == "Live Transition (Human -> AI Clone)":
            real_f = os.path.join(REAL_DIR, "real_human_slt_0001.wav")
            fake_f = os.path.join(FAKE_DIR, "fake_elevenlabs_roger.mp3")
            seq = [("Authentic Human Speech (CMU ARCTIC)", real_f), ("AI Voice Clone (ElevenLabs Roger)", fake_f)]
        elif stream_choice == "Continuous Authentic Human":
            real_f1 = os.path.join(REAL_DIR, "real_human_slt_0001.wav")
            real_f2 = os.path.join(REAL_DIR, "real_human_ksp_0002.wav")
            seq = [("Human Speaker 1 (American)", real_f1), ("Human Speaker 2 (Indian Accent)", real_f2)]
        else:
            fake_f1 = os.path.join(FAKE_DIR, "fake_elevenlabs_roger.mp3")
            fake_f2 = os.path.join(FAKE_DIR, "fake_bark_spk1_019.wav")
            seq = [("ElevenLabs Cloned Voice (Roger)", fake_f1), ("Bark Cloned Voice", fake_f2)]
            
        status_box = st.empty()
        badge_box = st.empty()
        gauge_box = st.empty()
        branch_box = st.empty()
        diag_box = st.empty()
        chart_box = st.empty()
        
        history_times = []
        history_scores = []
        hop_samples = int(rt_detector.hop_duration * rt_detector.sr)
        global_t = 0.0
        
        for feed_label, fpath in seq:
            audio = load_and_standardize_audio(fpath, target_sr=rt_detector.sr)
            n_chunks = len(audio) // hop_samples
            
            for c_idx in range(n_chunks):
                chunk = audio[c_idx * hop_samples:(c_idx + 1) * hop_samples]
                res = rt_detector.process_chunk(chunk)
                global_t += rt_detector.hop_duration
                
                history_times.append(round(global_t, 1))
                history_scores.append(res["final_score"])
                
                is_fake = res["prediction"] == "FAKE"
                status_box.markdown(f"**Current Audio Stream Feed:** `{feed_label}` | Stream Time: `{global_t:.1f}s` | Latency: `{res['latency_ms']}ms`")
                
                if res["speech_detected"]:
                    if is_fake:
                        badge_box.markdown('<div class="badge-fake">🚨 AI CLONED SPEECH DETECTED</div>', unsafe_allow_html=True)
                    else:
                        badge_box.markdown('<div class="badge-real">✅ AUTHENTIC HUMAN SPEECH</div>', unsafe_allow_html=True)
                        
                    gauge_box.progress(float(res["final_score"]))
                    gauge_box.caption(f"Composite Risk Score: **{res['final_score']:.3f}** (Threshold: {DECISION_THRESHOLD}) | Confidence: **{res['confidence']:.1f}%**")
                    
                    with branch_box.container():
                        b1, b2, b3 = st.columns(3)
                        b1.metric("Branch 1 (Wav2Vec2 SSL)", f"{res['branch1']:.3f}")
                        b2.metric("Branch 2 (Phase ResNet)", f"{res['branch2']:.3f}")
                        b3.metric("Branch 3 (Temporal/Bio)", f"{res['branch3']:.3f}")
                        
                    with diag_box.container():
                        d1, d2 = st.columns(2)
                        d1.metric("Detected Breaths", f"{res['breaths']}")
                        d2.metric("Local Jitter (pitch)", f"{res['jitter']:.4f}")
                else:
                    badge_box.info("⏸️ [VAD] Silence / No human speech detected in sliding window.")
                    
                # Update time-series plot
                fig, ax = plt.subplots(figsize=(10, 2.8))
                ax.plot(history_times, history_scores, color="#2563eb", marker="o", lw=2, label="Ensemble Risk Score")
                ax.axhline(0.50, color="#ef4444", linestyle="--", label="Decision Threshold (0.50)")
                ax.set_ylim(-0.05, 1.05)
                ax.set_xlabel("Stream Timeline (seconds)")
                ax.set_ylabel("Risk Score")
                ax.set_title("Real-Time Sliding Window Detection Timeline", fontsize=11, fontweight="bold")
                ax.grid(True, linestyle=":", alpha=0.5)
                ax.legend(loc="upper left")
                chart_box.pyplot(fig)
                plt.close(fig)
                
                time.sleep(update_speed)
                
        st.success("🏁 Live Real-Time Stream Session Completed.")

elif audio_bytes is not None:
    # Save audio temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
        tmp_file.write(audio_bytes)
        tmp_path = tmp_file.name
        
    try:
        col_player, col_meta = st.columns([2, 1])
        with col_player:
            st.subheader(f"Audio Playback: `{audio_filename}`")
            st.audio(audio_bytes)
            
        # Run detection
        with st.spinner("Analyzing spectral phase, prosody micro-perturbations, and SSL features..."):
            result = engine.predict_file(tmp_path)
            
        with col_meta:
            st.metric("Total Duration", f"{result['duration_seconds']}s")
            st.metric("Inference Latency", f"{result['latency_seconds']:.2f}s", f"{result['latency_per_chunk_seconds']:.2f}s/chunk")
            
        st.divider()
        
        # Main Decision Section
        res_col1, res_col2 = st.columns([1, 1])
        is_fake = result["overall_prediction"] == "FAKE"
        
        with res_col1:
            if is_fake:
                st.markdown('<div class="badge-fake">🚨 AI CLONED SPEECH DETECTED</div>', unsafe_allow_html=True)
                st.markdown('<div class="sub-badge">High probability of neural vocoder synthesis / voice conversion</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="badge-real">✅ AUTHENTIC HUMAN SPEECH</div>', unsafe_allow_html=True)
                st.markdown('<div class="sub-badge">Natural biological respiration and pitch micro-variations verified</div>', unsafe_allow_html=True)
                
        with res_col2:
            st.markdown(f"### Confidence: **{result['confidence_percentage']:.1f}%**")
            st.progress(float(result['confidence_percentage']) / 100.0)
            st.caption(f"Composite Ensemble Risk Score: **{result['overall_score']:.4f}** (Threshold: {DECISION_THRESHOLD:.2f})")
            
        st.write("")
        st.subheader("📊 3-Branch Forensic Breakdown")
        
        b_col1, b_col2, b_col3 = st.columns(3)
        b1_val = result["branch_scores"]["branch1_ssl"]
        b2_val = result["branch_scores"]["branch2_phase"]
        b3_val = result["branch_scores"]["branch3_temporal"]
        
        with b_col1:
            st.markdown("#### Branch 1: Wav2Vec2 SSL")
            st.caption("Weight: **50%** | Deep Acoustic Embeddings")
            st.metric("Branch Score", f"{b1_val:.3f}", delta=f"{'Fake' if b1_val > 0.5 else 'Real'}", delta_color="inverse")
            st.progress(min(max(b1_val, 0.0), 1.0))
            
        with b_col2:
            st.markdown("#### Branch 2: Phase ResNet-18")
            st.caption("Weight: **30%** | Vocoder Phase Incoherence")
            st.metric("Branch Score", f"{b2_val:.3f}", delta=f"{'Fake' if b2_val > 0.5 else 'Real'}", delta_color="inverse")
            st.progress(min(max(b2_val, 0.0), 1.0))
            
        with b_col3:
            st.markdown("#### Branch 3: Temporal & Biological")
            st.caption("Weight: **20%** | Jitter, Shimmer & Breathing")
            st.metric("Branch Score", f"{b3_val:.3f}", delta=f"{'Fake' if b3_val > 0.5 else 'Real'}", delta_color="inverse")
            st.progress(min(max(b3_val, 0.0), 1.0))
            
        st.divider()
        
        # Forensic Diagnostic Visualizations
        st.subheader("🔬 Acoustic & Biological Forensic Analysis")
        diag = result["diagnostics"]
        
        diag_col1, diag_col2, diag_col3, diag_col4 = st.columns(4)
        diag_col1.metric("Inhalation Breaths", f"{diag.get('breath_segment_count', 0)}", help="Human speech contains 100-1000Hz inhalation friction")
        diag_col2.metric("Silence Ratio", f"{diag.get('silence_ratio', 0.0)*100:.1f}%", help="Robotic digital silence indicates TTS pauses")
        diag_col3.metric("Local Jitter", f"{diag.get('jitter_local', 0.0):.4f}", help="Cycle-to-cycle pitch variability (<0.01 indicates flat TTS)")
        diag_col4.metric("Local Shimmer", f"{diag.get('shimmer_local', 0.0):.4f}", help="Cycle-to-cycle amplitude perturbation")
        
        # Dual-Channel Spectrogram Visualization (Branch 2)
        st.write("")
        st.write("#### Branch 2 Visualizer: Magnitude vs Instantaneous Frequency Deviation (Phase)")
        st.caption("Neural vocoders (HiFi-GAN, MelGAN) construct phase artificially, creating vertical streaking or unnatural discontinuities in the phase deviation channel.")
        
        # Extract phase spectrogram from the first chunk for plotting
        raw_clip = load_and_standardize_audio(tmp_path, target_sr=SAMPLE_RATE)[:SAMPLE_RATE * 4]
        from voice_cloning_detector.feature_extraction import compute_phase_spectrogram
        spec = compute_phase_spectrogram(raw_clip, sr=SAMPLE_RATE, target_frames=251)
        
        fig, axes = plt.subplots(1, 2, figsize=(12, 3.5))
        im0 = axes[0].imshow(spec[0], origin='lower', aspect='auto', cmap='magma')
        axes[0].set_title("Channel 0: Log-Magnitude STFT", fontsize=11, fontweight="bold")
        axes[0].set_xlabel("Time Frames")
        axes[0].set_ylabel("Frequency Bins")
        fig.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04)
        
        im1 = axes[1].imshow(spec[1], origin='lower', aspect='auto', cmap='viridis')
        axes[1].set_title("Channel 1: Instantaneous Frequency Deviation (Unwrapped Phase Derivative)", fontsize=11, fontweight="bold")
        axes[1].set_xlabel("Time Frames")
        axes[1].set_ylabel("Frequency Bins")
        fig.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04)
        plt.tight_layout()
        st.pyplot(fig)
        plt.close(fig)
        
        # Multi-chunk timeline if audio duration > 4 seconds
        if result["chunks_analyzed"] > 1:
            st.write("#### Temporal Risk Timeline Across Audio Slices")
            chunk_times = [c["start_time_sec"] for c in result["chunk_breakdown"]]
            chunk_scores = [c["score"] for c in result["chunk_breakdown"]]
            
            fig_timeline, ax = plt.subplots(figsize=(10, 2.5))
            ax.plot(chunk_times, chunk_scores, marker='o', color="#ef4444" if is_fake else "#10b981", lw=2)
            ax.axhline(0.50, color="#9ca3af", linestyle="--", label="Decision Threshold (0.50)")
            ax.set_ylim(-0.05, 1.05)
            ax.set_xlabel("Time (seconds)")
            ax.set_ylabel("Cloning Risk Score")
            ax.set_title("Sliding Window Score Profile")
            ax.grid(True, linestyle=":", alpha=0.5)
            ax.legend()
            st.pyplot(fig_timeline)
            plt.close(fig_timeline)
            
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
            
else:
    st.info("👈 Select or record an audio file in the sidebar to begin voice cloning analysis.")
    st.markdown("""
    ### About the 3-Branch Architecture
    
    1. **Branch 1: Pretrained Self-Supervised Wav2Vec 2.0 (Weight 50%)**
       - Captures high-level phonemic context and acoustic representations.
       - Frozen backbone ensures zero catastrophic forgetting.
       - Multi-layer weighted hidden state pooling targets subtle neural generator artifacts.
       
    2. **Branch 2: Phase-Aware ResNet-18 (Weight 30%)**
       - Direct inspection of the instantaneous frequency deviation: $\\frac{\\partial \\phi(t)}{\\partial t}$.
       - Neural vocoders (HiFi-GAN, MelGAN, BigVGAN) generate phase artificially from mel-spectrograms, leaving characteristic high-frequency phase smearing.
       
    3. **Branch 3: Hand-Crafted Temporal & Biological Artifacts (Weight 20%)**
       - Evaluates pitch **Jitter** (period perturbation) & **Shimmer** (amplitude perturbation).
       - Detects the presence of biological **inhalation breath sounds** (100–1000 Hz) during pauses.
       - Detects unnaturally sterile digital silence or static sub-band variances typical of auto-regressive TTS (ElevenLabs, XTTS, Bark).
    """)
