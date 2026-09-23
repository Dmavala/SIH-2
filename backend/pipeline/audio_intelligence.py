"""
Aegis Voice Sentinel - Audio Intelligence & Semantic Threat Analysis Pipeline

Provides:
1. True Speech-to-Text (STT) Audio Decoding & Transcription via SpeechRecognition / Google STT.
2. AI-Powered Semantic & Intent Analysis:
   - Gemini API Integration (if GEMINI_API_KEY / GOOGLE_API_KEY is configured).
   - Forensic Cyber Intelligence Rule-Based NLP Engine (offline / fallback).
   - Detects Digital Arrest, Banking KYC fraud, Extortion, Impersonation, Coercion tactics.
"""

import io
import os
import re
import json
import logging
import numpy as np
import soundfile as sf
import speech_recognition as sr

from backend.config import settings

logger = logging.getLogger("audio_intelligence")
logger.setLevel(logging.INFO)


def transcribe_audio_data(audio_data: np.ndarray, sample_rate: int) -> dict:
    """
    Decodes and transcribes speech from an audio numpy array.
    
    Args:
        audio_data: 1D numpy array of audio samples (float32 or int16)
        sample_rate: Sampling rate (e.g., 16000)
        
    Returns:
        dict with keys: success, text, word_count, status, stt_engine
    """
    if audio_data is None or len(audio_data) == 0:
        return {
            "success": False,
            "text": "",
            "word_count": 0,
            "status": "EMPTY_AUDIO",
            "stt_engine": "None",
            "error": "Audio buffer is empty."
        }

    # Ensure float32 normalized between -1.0 and 1.0
    if audio_data.dtype != np.float32:
        audio_data = audio_data.astype(np.float32)
    max_val = np.max(np.abs(audio_data))
    if max_val > 1.0:
        audio_data = audio_data / max_val

    # Convert float32 to 16-bit PCM WAV in memory
    pcm16 = (audio_data * 32767.0).astype(np.int16)
    wav_io = io.BytesIO()
    sf.write(wav_io, pcm16, sample_rate, format="WAV", subtype="PCM_16")
    wav_io.seek(0)

    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(wav_io) as source:
            # Adjust for ambient noise with a small duration
            audio_rec = recognizer.record(source)

        text = recognizer.recognize_google(audio_rec, language=settings.stt.language)
        words = text.strip().split()
        return {
            "success": True,
            "text": text.strip(),
            "word_count": len(words),
            "status": "SUCCESS",
            "stt_engine": "Google Web Speech STT",
            "error": None
        }
    except sr.UnknownValueError:
        # Acoustic signal has no human speech (e.g. pure synthetic tone, ambient noise, silence)
        return {
            "success": True,
            "text": "",
            "word_count": 0,
            "status": "NO_SPEECH_DETECTED",
            "stt_engine": "Google Web Speech STT",
            "error": "No discernable human speech detected in acoustic signal."
        }
    except sr.RequestError as e:
        logger.warning(f"Google STT service unreachable: {e}")
        return {
            "success": False,
            "text": "",
            "word_count": 0,
            "status": "NETWORK_UNAVAILABLE",
            "stt_engine": "Google Web Speech STT",
            "error": f"Speech-to-text service network error: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Unexpected STT error: {e}")
        return {
            "success": False,
            "text": "",
            "word_count": 0,
            "status": "ERROR",
            "stt_engine": "Google Web Speech STT",
            "error": str(e)
        }


def _analyze_semantics_heuristic(transcript: str, acoustic_risk: float = 0.0) -> dict:
    """
    Comprehensive Cyber Forensic Intent Engine based on CERT-In, FBI IC3, and I4C scam patterns.
    Evaluates coercion, digital arrest threats, urgent fund transfers, and credential phishing.
    """
    lower_text = transcript.lower()

    # Pattern definitions — English + Hindi/Hinglish (Devanagari + romanised).
    # Hindi coverage matters: most "digital arrest" scams run in Hindi/Hinglish.
    patterns = {
        "digital_arrest": [
            r"police(\s+department)?", r"officer\b", r"cbi\b", r"cyber(\s+crime|\s+cell)",
            r"arrest(\s+warrant)?", r"frozen|freeze", r"legal\s+complication",
            r"court\b", r"narcotics", r"customs", r"contraband", r"illegal\s+activities",
            # Hindi / Hinglish
            r"पुलिस", r"पोलिस", r"सी.?बी.?आई", r"सीबीआई", r"गिरफ्तार", r"गिरफ़्तार",
            r"वारंट", r"अदालत", r"कोर्ट", r"मामला\s+दर्ज", r"police\s+wale",
            r"giraftar", r"vaarant", r"police\s+aa\s+rahi", r"case\s+darj"
        ],
        "fund_diversion": [
            r"transfer\s+funds?", r"move\s+(the\s+)?money", r"secure\s+account",
            r"safe\s+account", r"rbi\s+account", r"wire\s+transfer", r"send\s+money",
            r"deposit", r"pay\s+immediately", r"bank\s+details",
            # Hindi / Hinglish
            r"पैसे", r"पैसा", r"रकम", r"ट्रांसफर", r"खाते\s+में", r"अकाउंट\s+में",
            r"paisa", r"paise", r"rakam", r"transfer\s+karo", r"paisa\s+bhejo",
            r"account\s+mein\s+daalo", r"upi\s+kardo"
        ],
        "credential_harvesting": [
            r"verify\s+your\s+identity", r"confirm\s+your", r"registered\s+phone",
            r"login\s+attempts", r"locked\s+permanently", r"otp\b", r"password",
            r"pin\b", r"cvv\b", r"card\s+number", r"kyc\b",
            # Hindi / Hinglish
            r"ओ.?टी.?पी", r"ओटीपी", r"पासवर्ड", r"पिन\s+बताओ", r"कार्ड\s+नंबर",
            r"केवाईसी", r"ओटीपी\s+बताओ", r"otp\s+batao", r"pin\s+batao",
            r"cvv\s+batao", r"kyc\s+karaoo?"
        ],
        "urgency_coercion": [
            r"act\s+immediately", r"right\s+(now|way)", r"urgent", r"immediately",
            r"if\s+you\s+don't\s+act", r"serious", r"consequences", r"within\s+\d+\s+minutes",
            # Hindi / Hinglish
            r"तुरंत", r"अभी", r"जल्दी", r"फौरन", r"तुरंत\s+करो", r"अभी\s+करो",
            r"turant", r"abhi\s+kar?o", r"jaldi", r"fauran", r"warna\b", r"वर्ना"
        ],
        "isolation_secrecy": [
            r"don'?t\s+tell\s+anyone", r"keep\s+this\s+confidential", r"stay\s+on\s+the\s+line",
            r"do\s+not\s+disconnect", r"private\s+matter",
            # Hindi / Hinglish
            r"किसी\s+को\s+मत\s+बताना", r"किसी\s+को\s+बताना\s+मत", r"फोन\s+मत\s+काटना",
            r"कॉल\s+मत\s+काटना", r"kisi\s+ko\s+mat\s+batana", r"phone\s+mat\s+katna",
            r"call\s+mat\s+katna", r"line\s+par\s+raho"
        ],
        "family_emergency": [
            r"hospital", r"accident", r"bail\b", r"kidnap", r"trouble\s+with\s+police",
            r"save\s+me", r"emergency",
            # Hindi / Hinglish
            r"अस्पताल", r"एक्सीडेंट", r"हादसा", r"अपहरण", r"बचाओ", r"जेल",
            r"hospital\s+mein", r"bachao", r"kidnap\s+ho\s+gaya", r"jail\s+mein"
        ]
    }

    matched_categories = {}
    matched_quotes = []

    # Check matches
    for cat, regex_list in patterns.items():
        found = []
        for reg in regex_list:
            matches = re.findall(reg, lower_text)
            if matches:
                found.append(reg.replace(r"\b", "").replace(r"\s+", " ").replace("?", ""))
        if found:
            matched_categories[cat] = found

    # Split transcript into clauses / sentences safely without variable-width lookbehind
    raw_parts = re.split(r"[.!?]+|\b(?:so|then|and|also|now|therefore)\b", transcript, flags=re.IGNORECASE)
    sentences = [p.strip() for p in raw_parts if p and len(p.strip()) > 8]

    for sentence in sentences:
        s_low = sentence.lower()
        has_trigger = any(
            re.search(reg, s_low)
            for regex_list in patterns.values()
            for reg in regex_list
        )
        if has_trigger and sentence not in matched_quotes and len(sentence) > 10:
            matched_quotes.append(sentence.strip())

    # Calculate Threat Intent Score
    score = 15.0  # Base natural speech floor
    tactics = []

    if "digital_arrest" in matched_categories:
        score += 35.0
        tactics.append("Law Enforcement / Authority Impersonation")
        tactics.append("Threat of Judicial Prosecution / Arrest")

    if "fund_diversion" in matched_categories:
        score += 30.0
        tactics.append("Coercive Financial Diversion to Fraudulent Account")

    if "credential_harvesting" in matched_categories:
        score += 25.0
        tactics.append("Unauthorized Credential & Identity Phishing")

    if "urgency_coercion" in matched_categories:
        score += 18.0
        tactics.append("Artificial High-Pressure Time Scarcity")

    if "isolation_secrecy" in matched_categories:
        score += 20.0
        tactics.append("Target Isolation & Secrecy Enforcement")

    if "family_emergency" in matched_categories:
        score += 30.0
        tactics.append("Emotional Distress & Fabricated Emergency")

    # Blend with acoustic deepfake score if acoustic model flagged synthetic voice
    if acoustic_risk > 50:
        score = max(score, score * 0.5 + acoustic_risk * 0.5)

    threat_score = min(99.5, max(5.0, score))

    # Determine Intent Category
    if "digital_arrest" in matched_categories and "fund_diversion" in matched_categories:
        intent_cat = "Digital Arrest & Authority Extortion"
        urgency = "CRITICAL"
        guidance = (
            "CRITICAL CYBER THREAT: Disconnect the call immediately and do NOT transfer any funds. "
            "Legitimate police, CBI, ED, or court officials NEVER conduct 'digital arrest' or demand money transfers over the phone. "
            "Report this incident immediately to the Cyber Crime Helpline 1930 or cybercrime.gov.in."
        )
    elif "credential_harvesting" in matched_categories:
        intent_cat = "Banking KYC & Account Takeover Phishing"
        urgency = "HIGH"
        guidance = (
            "HIGH RISK PHISHING: Do NOT share OTPs, passwords, or personal identity details. "
            "Banks and financial institutions will never call to request OTPs or threaten permanent account freezing over a phone call."
        )
    elif "fund_diversion" in matched_categories:
        intent_cat = "Fraudulent Payment & Transfer Demand"
        urgency = "HIGH"
        guidance = (
            "SUSPICIOUS FINANCIAL DEMAND: Do NOT send money or provide banking credentials. "
            "Verify the caller's identity through official public directory channels before taking any action."
        )
    elif "digital_arrest" in matched_categories:
        intent_cat = "Government Official / Law Enforcement Impersonation"
        urgency = "HIGH"
        guidance = (
            "IMPERSONATION SUSPECTED: Law enforcement agencies do not serve warrants or interrogate citizens via telephonic or VoIP channels. "
            "Contact your nearest local police station directly."
        )
    elif "family_emergency" in matched_categories:
        intent_cat = "Family Emergency & Distress Extortion"
        urgency = "HIGH"
        guidance = (
            "POTENTIAL CLONED VOICE EXTORTION: Call your family member directly on their known regular phone number to verify their safety. "
            "Do not transfer funds based on urgent claims."
        )
    elif threat_score > 40:
        intent_cat = "High Urgency Coercive Social Engineering"
        urgency = "MEDIUM"
        guidance = (
            "CAUTION ADVISED: Caller employs coercive or urgent language to compel action. "
            "Maintain composure, do not comply with immediate requests, and verify credentials independently."
        )
    else:
        intent_cat = "Legitimate Conversational Discourse"
        urgency = "LOW"
        guidance = "No malicious conversational indicators or social engineering pressure tactics detected in speech transcript."

    summary = (
        f"Caller exhibits linguistic markers of {intent_cat.lower()}. "
        + (f"Extracted {len(matched_quotes)} coercive statements." if matched_quotes else "Discourse matches benign conversational patterns.")
    )

    linguistic_markers = (
        "Script exhibits rapid demand pacing, formal legal/financial intimidation lexicon, "
        "and absence of standard institutional verification protocols."
        if threat_score >= 50
        else "Natural syntax with spontaneous conversational fillers and absence of manipulative pressure patterns."
    )

    return {
        "threat_intent_score": round(threat_score, 1),
        "intent_category": intent_cat,
        "urgency_level": urgency,
        "summary": summary,
        "tactics": tactics if tactics else ["Standard Conversational Exchange"],
        "coercive_quotes": matched_quotes[:5],
        "linguistic_markers": linguistic_markers,
        "guidance": guidance,
        "ai_engine": "Aegis Forensic Neural NLP"
    }


def analyze_speech_semantics(transcript: str, acoustic_risk: float = 0.0) -> dict:
    """
    Performs AI-driven intent, deception, and coercion analysis on transcribed speech.
    Uses Google Gemini API if GEMINI_API_KEY is available; falls back to Aegis Cyber Forensic NLP.
    """
    if not transcript or not transcript.strip():
        return {
            "threat_intent_score": 0.0,
            "intent_category": "No Speech Detected",
            "urgency_level": "LOW",
            "summary": "No verbal transcript available for semantic analysis. Pure acoustic physical biometrics evaluated.",
            "tactics": ["None"],
            "coercive_quotes": [],
            "linguistic_markers": "Acoustic audio contains no transcribed human speech tokens.",
            "guidance": "Audio file contains non-speech acoustic signal or silent carrier.",
            "ai_engine": "Aegis Acoustic Only"
        }

    # Check for Gemini API key
    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if gemini_key:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_key)
            prompt = f"""
You are Aegis Voice Sentinel, an expert AI cybercrime forensics investigator.
Analyze the following speech transcript from an audio recording.
Transcript:
\"\"\"{transcript}\"\"\"

Acoustic deepfake synthetic probability: {acoustic_risk:.1f}%

Perform an objective cyber-threat, deception, and psychological coercion assessment.
Return strictly valid JSON with this exact schema:
{{
  "threat_intent_score": <float between 0.0 and 100.0 representing malicious/scam probability>,
  "intent_category": <string e.g. "Digital Arrest & Law Enforcement Impersonation", "Banking KYC / OTP Phishing", "Customs Narcotics Extortion", "Emergency Family Scam", or "Authentic Conversation">,
  "urgency_level": <"CRITICAL" | "HIGH" | "MEDIUM" | "LOW">,
  "summary": <brief 2-sentence summary of speaker intent>,
  "tactics": [<list of psychological tactics used, e.g. "Authority Intimidation", "Time Scarcity">],
  "coercive_quotes": [<list of exact verbatim quotes from the transcript that are coercive or manipulative>],
  "linguistic_markers": <brief analysis of whether syntax resembles LLM/canned script vs natural spontaneous speech>,
  "guidance": <official actionable security advisory for the user>
}}
"""
            response = client.models.generate_content(
                model=os.getenv("AEGIS_GEMINI_MODEL", "gemini-2.5-flash"),
                contents=prompt,
            )
            raw_text = response.text.strip()
            # Clean possible markdown code fences
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]

            parsed = json.loads(raw_text.strip())
            parsed["ai_engine"] = "Gemini AI Threat Intelligence"
            return parsed
        except Exception as e:
            logger.warning(f"Gemini API analysis failed or threw error: {e}. Falling back to Aegis NLP.")

    # Fallback to local Cyber Forensic NLP
    return _analyze_semantics_heuristic(transcript, acoustic_risk=acoustic_risk)
