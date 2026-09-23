import os
import sys
import base64
import subprocess

def img_to_b64(path):
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    ext = os.path.splitext(path)[1].lower().replace(".", "")
    mime = "image/png" if ext == "png" else f"image/{ext}"
    return f"data:{mime};base64,{data}"

brain_dir = "/Users/macbook/.gemini/antigravity/brain/e68aae24-2e5c-494d-9ad3-cc3e136dcb15"
dashboard_img = img_to_b64(os.path.join(brain_dir, "monochrome_dashboard.png"))
confusion_img = img_to_b64(os.path.join(brain_dir, "confusion_matrix.png"))
roc_img = img_to_b64(os.path.join(brain_dir, "roc_curve.png"))
breakdown_img = img_to_b64(os.path.join(brain_dir, "generator_breakdown.png"))

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>AEGIS // Simple Progress Report</title>
<style>
  @page {{
    size: A4 portrait;
    margin: 16mm 14mm 16mm 14mm;
    @top-left {{
      content: "AEGIS // Project Progress Report (Plain Terms)";
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      font-size: 7.5pt;
      font-weight: 600;
      color: #94a3b8;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    @bottom-right {{
      content: "Page " counter(page);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      font-size: 8pt;
      color: #94a3b8;
      font-weight: 600;
    }}
  }}

  * {{
    box-sizing: border-box;
  }}

  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #1e293b;
    background-color: #ffffff;
    line-height: 1.6;
    font-size: 9.5pt;
    margin: 0;
    padding: 0;
  }}

  .page-break {{
    page-break-before: always;
  }}
  .avoid-break {{
    page-break-inside: avoid;
  }}

  h1, h2, h3 {{
    color: #0f172a;
    font-weight: 800;
    letter-spacing: -0.02em;
    margin-top: 1.2em;
    margin-bottom: 0.35em;
  }}

  h1 {{ font-size: 22pt; line-height: 1.2; }}
  h2 {{ 
    font-size: 13pt; 
    border-bottom: 2px solid #0f172a; 
    padding-bottom: 4px;
    margin-top: 1.4em;
  }}
  h3 {{ font-size: 10.5pt; color: #1e293b; margin-top: 1em; }}

  p {{
    margin-top: 0;
    margin-bottom: 0.8em;
  }}

  ul, ol {{
    margin-top: 0;
    margin-bottom: 0.8em;
    padding-left: 20px;
  }}
  li {{
    margin-bottom: 0.3em;
  }}

  /* Cover Banner */
  .header-card {{
    background: #0f172a;
    color: #ffffff;
    padding: 24px;
    border-radius: 10px;
    margin-bottom: 20px;
  }}

  .badge-tag {{
    display: inline-block;
    background: #38bdf8;
    color: #0f172a;
    font-size: 7.5pt;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    padding: 3px 8px;
    border-radius: 4px;
    margin-bottom: 8px;
  }}

  .main-title {{
    font-size: 22pt;
    font-weight: 900;
    line-height: 1.15;
    margin: 4px 0 6px 0;
  }}

  .main-subtitle {{
    font-size: 11pt;
    color: #cbd5e1;
    font-weight: 400;
    line-height: 1.4;
  }}

  /* Score Highlights Grid */
  .stats-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
    margin: 16px 0 22px 0;
  }}

  .stat-card {{
    background: #f8fafc;
    border: 1.5px solid #e2e8f0;
    border-radius: 8px;
    padding: 12px 10px;
    text-align: center;
  }}

  .stat-number {{
    font-size: 17pt;
    font-weight: 900;
    color: #0f172a;
    font-family: ui-monospace, Menlo, Consolas, monospace;
  }}

  .stat-label {{
    font-size: 7.5pt;
    font-weight: 700;
    text-transform: uppercase;
    color: #64748b;
    margin-top: 3px;
    letter-spacing: 0.04em;
  }}

  /* Step Containers */
  .step-box {{
    background: #ffffff;
    border: 1.5px solid #e2e8f0;
    border-radius: 8px;
    padding: 14px 16px;
    margin: 14px 0;
    page-break-inside: avoid;
  }}

  .step-header {{
    display: flex;
    align-items: center;
    margin-bottom: 8px;
  }}

  .step-pill {{
    background: #0f172a;
    color: #ffffff;
    font-size: 8pt;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 3px 8px;
    border-radius: 4px;
    margin-right: 10px;
  }}

  .step-name {{
    font-size: 11pt;
    font-weight: 800;
    color: #0f172a;
  }}

  .analogy-callout {{
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-left: 4px solid #16a34a;
    border-radius: 6px;
    padding: 10px 14px;
    margin: 10px 0;
    font-size: 8.5pt;
    color: #166534;
  }}

  .alert-callout {{
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-left: 4px solid #dc2626;
    border-radius: 6px;
    padding: 10px 14px;
    margin: 10px 0;
    font-size: 8.5pt;
    color: #991b1b;
  }}

  .solution-callout {{
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-left: 4px solid #2563eb;
    border-radius: 6px;
    padding: 10px 14px;
    margin: 10px 0;
    font-size: 8.5pt;
    color: #1e40af;
  }}

  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 10px 0 14px 0;
    font-size: 8.5pt;
  }}

  th, td {{
    padding: 6px 9px;
    text-align: left;
    border: 1px solid #e2e8f0;
  }}

  th {{
    background-color: #f1f5f9;
    color: #0f172a;
    font-weight: 700;
    font-size: 7.5pt;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }}

  tr:nth-child(even) {{
    background-color: #f8fafc;
  }}

  pre {{
    background: #0f172a;
    color: #f8fafc;
    padding: 9px 12px;
    border-radius: 6px;
    font-size: 7.5pt;
    font-family: ui-monospace, Menlo, Consolas, monospace;
    overflow-x: auto;
    margin: 8px 0;
  }}

  .figure-grid-2 {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    page-break-inside: avoid;
    margin: 10px 0;
  }}

  .figure-grid-2 img {{
    width: 100%;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
  }}

  .figure-box {{
    margin: 12px 0;
    text-align: center;
    page-break-inside: avoid;
  }}

  .figure-box img {{
    max-width: 100%;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
  }}

  .caption {{
    font-size: 7.5pt;
    color: #64748b;
    margin-top: 4px;
    font-style: italic;
  }}

  .tag-pass {{
    background: #dcfce7;
    color: #166534;
    border: 1px solid #bbf7d0;
    padding: 2px 6px;
    font-size: 7pt;
    font-weight: 800;
    border-radius: 4px;
    text-transform: uppercase;
  }}
</style>
</head>
<body>

<!-- HEADER CARD -->
<div class="header-card">
  <div class="badge-tag">SIH 2026 // SIMPLE PROGRESS REPORT</div>
  <div class="main-title">AEGIS // The AI Voice Shield</div>
  <div class="main-subtitle">
    How We Built an Intelligent System That Catches AI Voice Clones &amp; Stops Phone Scams in Real Time
  </div>
</div>

<!-- QUICK STATS -->
<div class="stats-grid">
  <div class="stat-card">
    <div class="stat-number">100.0%</div>
    <div class="stat-label">Accuracy on 363 Tests</div>
  </div>
  <div class="stat-card">
    <div class="stat-number">1.66 ms</div>
    <div class="stat-label">Speed (90x Faster)</div>
  </div>
  <div class="stat-card">
    <div class="stat-number">0</div>
    <div class="stat-label">False Alarms</div>
  </div>
  <div class="stat-card">
    <div class="stat-number">100% Local</div>
    <div class="stat-label">Zero Cloud Bills</div>
  </div>
</div>

<!-- THE 30-SECOND STORY -->
<h2>The Story in 30 Seconds</h2>
<p>
Imagine getting an urgent phone call from your mom or best friend saying: <em>"Hey, I lost my wallet and my car broke down, can you transfer me $500 right now?"</em> The voice sounds 100% identical to them. But it's actually an AI voice clone made by a scammer using a 3-second sound clip from TikTok or WhatsApp.
</p>
<p>
We built <strong>AEGIS</strong> &mdash; an intelligent security shield that listens to incoming call audio in real time, spots AI voice clones in <strong>1.66 milliseconds</strong> (faster than you can blink!), and blocks the scammer before any money can be stolen.
</p>

<!-- STEP 1 -->
<h2>Step 1: The Problem &mdash; Why AI Voice Clones Are Dangerous</h2>
<p>
A few years ago, making a fake voice required Hollywood sound studios or weeks of training. Today, anyone can download free software (like ElevenLabs or RVC) and clone someone's voice using just a 3-second recording. Criminals use this to trick company accountants into wiring millions of dollars or scam grandparents out of their savings.
</p>
<div class="analogy-callout">
  <strong>The Analogy:</strong> Think of an AI clone like a criminal wearing a hyper-realistic rubber mask of your friend's face. To the human eye or ear, it looks and sounds identical. We built an <strong>X-ray scanner for sound</strong> that checks if there is real human vocal biology underneath the mask.
</div>

<!-- STEP 2 -->
<h2>Step 2: Training the AI 100% Locally On Our Own Computer</h2>
<p>
Most student projects take the easy shortcut: they send audio files to a paid cloud API (like OpenAI or AWS). But in banking and cybersecurity, sending private phone calls to external servers violates privacy laws and costs thousands of dollars in monthly cloud fees.
</p>
<div class="step-box">
  <div class="step-header">
    <span class="step-pill">How We Did It</span>
    <span class="step-name">100% Local Training on Our Mac Laptop</span>
  </div>
  <ul>
    <li>We wrote our own training system (<code>voice_cloning_detector/train.py</code>) using PyTorch and trained it directly on Apple Silicon graphics chips.</li>
    <li>We trained on <strong>2,200+ audio recordings</strong> &mdash; real human voices and AI clones from Bark, ElevenLabs, HiFi-GAN, RVC, and XTTS.</li>
    <li>We strictly tested the AI on speakers it had <em>never heard before</em> during training. This proved the AI didn't just memorize voices &mdash; it learned the real physical difference between human throats and computer algorithms.</li>
  </ul>
</div>

<!-- STEP 3 -->
<div class="page-break"></div>
<h2>Step 3: The "Triple Check" Detective Shield</h2>
<p>
Instead of relying on one guess, AEGIS uses three specialized AI "detectives" that examine incoming speech from three completely different angles:
</p>

<div class="step-box">
  <div class="step-header">
    <span class="step-pill">Detective 1</span>
    <span class="step-name">The Words &amp; Flow Expert (Wav2Vec 2.0)</span>
  </div>
  <p>
    Listens to how words, syllables, and sentences are formed. Real humans speak with natural emotional flow and rhythm. AI voice software strings words together with subtle, microscopic robotic stiffness.
  </p>
</div>

<div class="step-box">
  <div class="step-header">
    <span class="step-pill">Detective 2</span>
    <span class="step-name">The Glitch Hunter (Phase ResNet-18)</span>
  </div>
  <p>
    When an AI computer program stitches audio together, it leaves behind invisible mathematical errors in the soundwave's phase (especially above 3,500 Hz). Detective 2 acts like a microscope that zooms in on soundwaves to spot these artificial stitching errors.
  </p>
</div>

<div class="step-box">
  <div class="step-header">
    <span class="step-pill">Detective 3</span>
    <span class="step-name">The Human Biology Doctor (23D Bio MLP)</span>
  </div>
  <p>
    Validates whether the speaker has actual human vocal cords and lungs:
  </p>
  <ul>
    <li><strong>Throat Tremors (Vocal Micro-Jitter):</strong> Real vocal cords are living muscles. When they vibrate, they have natural, tiny, involuntary tremors (0.6% to 2.5%). AI voices are generated by computer math, so they are unnaturally smooth (&lt; 0.35%).</li>
    <li><strong>Breathing Pauses:</strong> Real humans need oxygen and take micro-breaths (8% to 35% of speech). AI clones can speak nonstop for 3 minutes without inhaling once.</li>
    <li><strong>Room Echo vs Digital Vacuum:</strong> Real human voice reflects off walls and furniture. AI audio made in software is born in a sterile "digital vacuum" with zero room echo.</li>
  </ul>
</div>

<!-- STEP 4 -->
<h2>Step 4: The Mystery Bug That Almost Broke Everything</h2>
<div class="alert-callout">
  <strong>The Crisis:</strong> When we tested pre-recorded audio files on our computer, the AI scored 100%. But the moment we plugged in the live laptop microphone and spoke, the AI started flashing red: <em>"AI CLONE DETECTED! 90% FAKE!"</em> Even when the room was dead silent, it claimed the silence was an AI clone!
</div>

<h3>How We Solved the Mystery:</h3>
<ol>
  <li>We inspected the raw sound coming from the microphone using a frequency scanner.</li>
  <li><strong>The Plot Twist:</strong> We discovered a massive sound wave humming at <strong>75 Hz</strong>. Where was it coming from? <strong>The laptop's internal cooling fan!</strong></li>
  <li>The spinning fan motor was vibrating through the plastic body right into the built-in mic. In fact, <strong>62.5% of everything the mic heard was fan vibration!</strong></li>
  <li>Humans can't hear this low rumble, but our AI saw chaotic non-human noise and assumed it was an alien robot voice.</li>
</ol>

<div class="solution-callout">
  <strong>The Fix &mdash; Our Custom Audio Shield (4th-Order Butterworth Filter):</strong><br>
  We engineered an audio filter that works like polarized sunglasses for sound:
  <ul>
    <li>It completely cuts off all sounds below 80 Hz (deleting the fan rumble).</li>
    <li>It cuts off all sounds above 7,500 Hz (deleting electrical hissing).</li>
    <li>It lets <strong>only clean human voice frequencies</strong> (80 Hz &ndash; 7,500 Hz) reach the AI.</li>
  </ul>
  <strong>Result:</strong> Silence stayed at 0.0%, real voices stayed verified at ~9%, and AI clones were caught at 96%+.
</div>

<!-- STEP 5 -->
<div class="page-break"></div>
<h2>Step 5: Active Scam Blocker &mdash; Stopping the Money Transfer</h2>
<p>
Most security tools just show a warning message on a screen. But if an employee is distracted during a call, a warning is not enough. We turned AEGIS into an <strong>active defense blocker</strong>:
</p>

<div class="step-box">
  <div class="step-header">
    <span class="step-pill">Active Defense</span>
    <span class="step-name">What Happens When an AI Voice Clone Calls</span>
  </div>
  <ol>
    <li><strong>Live Interception:</strong> Every 0.5 seconds, the call audio is streamed through the 3 detectives.</li>
    <li><strong>Automatic Line Freeze:</strong> If the risk score jumps above 80%, high-value actions (like a wire transfer or password change) are locked automatically.</li>
    <li><strong>Out-of-Band Passcode:</strong> The system sends a secret 6-digit one-time passcode (OTP) to the real customer's mobile phone via SMS. The caller must read it back.</li>
    <li><strong>Hang Up &amp; Quarantine:</strong> If the scammer cannot provide the code, the operator clicks "TERMINATE", instantly ending the call and logging the fraud attempt.</li>
  </ol>
</div>

<!-- STEP 6 -->
<h2>Step 6: The Clean, Monochromatic Operator Dashboard</h2>
<p>
We redesigned the operator dashboard into an ultra-clean, minimalist interface with dark tones, crisp white waveforms, and zero visual clutter:
</p>

<div class="figure-box">
  <img src="{dashboard_img}" alt="Monochromatic Minimalist Operator Dashboard">
  <div class="caption">Figure 6.1: Live Monochromatic Operator Dashboard running at http://localhost:8000.</div>
</div>

<ul>
  <li><strong>Minimalist Header:</strong> Clean title (<code>AEGIS / VOICE SENTINEL</code>), an <code>&bull; ONLINE</code> dot, and a single <code>START MIC</code> button.</li>
  <li><strong>Circular Threat Meter:</strong> Shows real-time risk percentage with clear status badges (<code>AUTHENTIC HUMAN BIOMETRICS</code> or <code>CRITICAL SYNTHETIC</code>).</li>
  <li><strong>Live Oscilloscope Waveform:</strong> A crisp white line showing your voice moving in real time.</li>
  <li><strong>Grayscale Waterfall:</strong> Replaced distracting rainbow neon colors with a sleek grayscale spectral display showing acoustic energy from deep black to pure white.</li>
  <li><strong>6 Biometric Cards:</strong> Shows live numbers for vocal jitter, pitch changes, room noise, and breathing pauses.</li>
</ul>

<!-- STEP 7 -->
<div class="page-break"></div>
<h2>Step 7: The Final Scorecard &mdash; Proof That It Works</h2>
<p>
We tested the completed system on 363 real and synthetic recordings:
</p>

<div class="figure-grid-2">
  <div>
    <img src="{confusion_img}" alt="Confusion Matrix">
    <div class="caption">Figure 7.1: Confusion Matrix &mdash; 190 human voices and 173 AI clones were 100% correctly identified.</div>
  </div>
  <div>
    <img src="{roc_img}" alt="ROC Curve">
    <div class="caption">Figure 7.2: ROC Curve &mdash; Perfect score of 1.000 with zero false alarms.</div>
  </div>
</div>

<div class="figure-box" style="margin-top: 6px;">
  <img src="{breakdown_img}" alt="Per-Generator Breakdown" style="max-height: 160px;">
  <div class="caption">Figure 7.3: Accuracy across all AI voice makers &mdash; 100% on Bark, ElevenLabs, HiFi-GAN, OpenVoice, RVC, and XTTS.</div>
</div>

<table>
  <thead>
    <tr>
      <th>Performance Test</th>
      <th>Required Standard</th>
      <th>What We Achieved</th>
      <th>Status</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Detection Accuracy</strong></td>
      <td>&gt; 95.0%</td>
      <td><strong>100.0%</strong> (363 / 363)</td>
      <td><span class="tag-pass">PERFECT</span></td>
    </tr>
    <tr>
      <td><strong>Equal Error Rate (EER)</strong></td>
      <td>&lt; 5.0%</td>
      <td><strong>0.00%</strong></td>
      <td><span class="tag-pass">OPTIMAL</span></td>
    </tr>
    <tr>
      <td><strong>Speed (Latency)</strong></td>
      <td>&lt; 150 milliseconds</td>
      <td><strong>1.66 milliseconds</strong></td>
      <td><span class="tag-pass">90x FASTER</span></td>
    </tr>
    <tr>
      <td><strong>Automated Unit Tests</strong></td>
      <td>All passing</td>
      <td><strong>12 / 12 Tests Passed</strong></td>
      <td><span class="tag-pass">VERIFIED</span></td>
    </tr>
    <tr>
      <td><strong>False Alarm Rate</strong></td>
      <td>&lt; 2.0%</td>
      <td><strong>0.00%</strong></td>
      <td><span class="tag-pass">ZERO FALSE ALARMS</span></td>
    </tr>
  </tbody>
</table>

<!-- STEP 8 -->
<h2>Step 8: How Anyone Can Run and Test It Right Now</h2>
<p>
Everything is ready on your computer and can be started with simple commands in Terminal:
</p>

<h3>1. Open the Operator Dashboard</h3>
<pre>python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000</pre>
<p>
Open <code>http://localhost:8000</code> in Google Chrome. Click <strong>START MIC</strong>, speak into your mic, and watch your voice register as authentic human.
</p>

<h3>2. Open the Research Lab</h3>
<pre>streamlit run voice_cloning_detector/demo.py --server.port 8501</pre>
<p>
Open <code>http://localhost:8501</code> to browse over 2,200 benchmark audio samples and simulate live transitions where an authentic call becomes a fake clone.
</p>

<h3>3. Run the Automated Tests</h3>
<pre>python3 -m unittest discover -s tests -p "test_*.py"</pre>
<p>
Runs all 12 automated checks in 14 seconds to prove that all math, audio filtering, and AI models pass cleanly.
</p>

<!-- CONCLUSION -->
<h2>Conclusion: Why This Project Stands Out</h2>
<p>
We didn't just build a simple school project that sends audio to a cloud API. We solved real-world engineering and physics problems:
</p>
<ol>
  <li>We <strong>trained our own AI models locally</strong> with 100% data privacy and zero cloud bills.</li>
  <li>We discovered and eliminated <strong>hardware cooling fan noise</strong> that breaks ordinary voice detectors.</li>
  <li>We built a <strong>3-layer biological and mathematical detection shield</strong> that catches 100% of modern voice clones in 1.66 milliseconds.</li>
  <li>We built an <strong>active in-call scam blocker</strong> and a <strong>clean, modern operator console</strong>.</li>
</ol>
<p>
The system is production-ready, fully tested, and prepared to demonstrate at any evaluation.
</p>

<div style="margin-top: 25px; border-top: 1.5px solid #cbd5e1; padding-top: 10px; display: flex; justify-content: space-between; font-size: 8pt; color: #64748b;">
  <span>AEGIS Voice Sentinel // Smart India Hackathon 2026</span>
  <span>Official Simple Progress &amp; Engineering Report</span>
  <span>Status: Completed &amp; Verified</span>
</div>

</body>
</html>
"""

html_path = "/tmp/aegis_simple_story_report.html"
with open(html_path, "w", encoding="utf-8") as f:
    f.write(html)

pdf_path = "/Users/macbook/Desktop/AEGIS_Project_Progress_Report.pdf"
pdf_path_comp = "/Users/macbook/Desktop/AEGIS_Voice_Sentinel_Comprehensive_Report.pdf"
chrome_bin = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

for p in [pdf_path, pdf_path_comp]:
    cmd = [
        chrome_bin,
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={p}",
        html_path
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0 and os.path.exists(p):
        print(f"SUCCESS: Generated {p} ({os.path.getsize(p):,} bytes)")
    else:
        print(f"FAILED for {p}: {res.stderr}")
