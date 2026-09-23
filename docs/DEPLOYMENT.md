# AEGIS Voice-Sentinel — Government Deployment Guide

This document describes what is production-ready today, what must be configured
before a MHA / I4C / DoT / RBI deployment, and what remains open. It is written
to be honest with reviewers — overclaiming is how systems get rejected.

---

## 1. Honest system status (read this first)

### What works and is verified
| Area | Status |
|---|---|
| Detection pipeline (2-engine consensus, INCONCLUSIVE abstention) | ✅ 54/54 tests pass |
| Evidence store (SQLite, SHA-256 hash-chained audit trail) | ✅ Tamper detection verified |
| OTP challenge (crypto-secure, salted-hash storage, lockout, TTL) | ✅ Brute-force tested |
| API security (API-key gate, rate limiting, frame caps, traversal guard) | ✅ |
| Forensic dossier (digest-basis disclosure, PDF/HTML export) | ✅ |
| Frontend (env-driven endpoints, hooks refactored) | ✅ builds clean |
| Training pipeline (real data, EER eval, resume, honest metadata) | ✅ runs on 194 in-repo clips |

### What is NOT production-grade yet — say this to reviewers before they ask
1. **Models are trained on only 194 in-repo clips** (YouTube speech, ElevenLabs/
   Play.ht/HiFi-GAN fakes, real scam calls). RawNet2 ranks this data perfectly
   (EER 0.0 on validation) but AASIST needs more epochs on larger corpora
   (val_acc ~0.76 on 167 in-repo clips). **Deployment claims require training on
   ASVspoof 2021 LA/Eval + in-country telephony recordings** — the pipeline is
   ready (`python -m backend.training.train`), the dataset acquisition is a
   procurement/registration task.
2. **Latency**: ~10–25 ms/frame CPU for two engines — meets real-time budgets for
   streaming; batch analysis of a full file runs ~0.4 s mean / 0.45 s p95 per
   clip (see `full_benchmark_report.json`), ~17 s under 8x concurrent load for
   the full-file forensic endpoint. Load test harness: `scripts/load_test.py`.
3. **The demo "authentic" samples are now real recordings** (legacy synthetic
   samples were removed — they made the original evaluation circular).
4. Full-corpus behaviour (167 real in-repo clips, `full_benchmark_report.json`,
   regenerable via `scripts/run_full_evaluation.py`): **0 deepfakes pass as
   authentic; 1/167 real clips flagged CRITICAL (0.6%); 91/167 crisp verdicts,
   90 correct; 76 escalated to human review** — safe, not yet sharp.
5. **Task-separation note (do not regress):** only synthetic-vs-real corpora
   train/evaluate the deepfake engines. Scam-content folders must never be
   labelled "fake" — their audio is real human speech; the semantics layer owns
   fraud content. A previous training round made that mistake and it degraded
   both engines measurably.

---

## 2. Production configuration (all via environment — nothing hardcoded)

```bash
cp .env.example .env
# REQUIRED for prod:
AEGIS_ENV=prod
AEGIS_CORS_ORIGINS=https://your-dashboard.gov.in
AEGIS_AUTH_ENABLED=1
AEGIS_API_KEY=<generate: python -c "import secrets; print(secrets.token_urlsafe(32))">
AEGIS_DB_BACKEND=sqlite            # or postgres (see pyproject extras)
AEGIS_DB_SQLITE_PATH=/var/lib/aegis/evidence.db
AEGIS_RELOAD=0

# Recommended after measuring on your own dev set:
AEGIS_CONSENSUS_W_AASIST=0.3
AEGIS_CONSENSUS_W_RAWNET=0.7
```

The app refuses to boot in `prod` mode if CORS/auth/persistence/reload settings
are unsafe (`settings.validate()`).

---

## 3. Evidence & chain of custody (Section 63, BSA 2023)

- Every audit event is hash-chained (`entry_hash = SHA-256(prev_hash + payload)`).
  `/api/audit-verify` recomputes the whole chain and reports the exact breaking
  event if any record was altered, inserted, or deleted.
- OTPs are stored **only as salted SHA-256 hashes** — a leaked DB cannot pass a
  pending challenge. The plaintext OTP is returned once, at issue time, for
  delivery over the out-of-band channel (SMS gateway integration is a
  deployment task — the code currently returns it to the operator console).
- Dossiers persist in the evidence DB and are retrievable at
  `/api/dossiers/{id}` with PDF/HTML export at `/api/dossiers/{id}/export`.
- **Digest honesty**: when raw audio is not retained (privacy-preserving mode),
  the dossier explicitly labels the digest as `TELEMETRY_DIGEST_ONLY`. For court
  submissions where audio retention is required, capture and store the PCM
  stream (retention policy = DPDP decision, not a code default).
- **Officer signature**: the certificate includes a signature block; cryptographic
  counter-signing via eSign/DSC must be integrated with a licensed CA — this is
  an integration, not implemented in-repo.

---

## 4. Container deployment

```bash
docker build -t aegis-voice-sentinel .
docker run -p 8000:8000 \
  -e AEGIS_ENV=prod -e AEGIS_CORS_ORIGINS=https://dashboard.gov.in \
  -e AEGIS_AUTH_ENABLED=1 -e AEGIS_API_KEY=... \
  -v aegis-data:/app/data \
  aegis-voice-sentinel
```

Health probe: `GET /api/health`. CI runs the full backend test-suite and the
frontend build on every push (`.github/workflows/ci.yml`).

---

## 5. Training / recalibration procedure

```bash
# 1. Acquire data (ASVspoof 2021 LA requires registration — see
#    datashare.ed.ac.uk). Lay out as:
#    <root>/real/*.flac  <root>/fake/*.flac   (or ASVspoof trial_metadata)
# 2. Train (resumable — run in chunks on modest hardware):
python -m backend.training.train --data-dir <root> --epochs 30 --arch both
python -m backend.training.train --data-dir <root> --epochs 20 --arch aasist --resume
# 3. Verify honestly:
python scripts/build_real_demo_samples.py   # rebuild demo files from corpora
python -m unittest discover -s tests        # full suite incl. classification
```

`backend/models/training_meta.json` records the data mode, clip count, epochs
and per-epoch EER — quote **this file**, not adjectives, in evaluations.

---

## 6. Pre-deployment checklist (STQC-aligned)

- [ ] Models retrained on ASVspoof 2021 LA + Indian telephony corpus; EER per
      attack family published from held-out data
- [ ] `AEGIS_ENV=prod` validation passes (CORS, auth, persistence, no reload)
- [ ] TLS termination (nginx/ALB) in front of uvicorn; HSTS enabled
- [ ] Evidence DB on persistent volume with backups; Postgres for HA
- [ ] SMS gateway wired for out-of-band OTP delivery (no on-screen OTP in prod)
- [ ] SIEM sink for audit events (export job) + `/api/audit-verify` monitoring
- [ ] Load test at target concurrency (baseline numbers from `scripts/load_test.py` / `load_test_report.json`)
- [ ] DPDP data-retention decision documented (audio retained or telemetry-only)
- [ ] eSign/DSC integration for Section 63(4) officer certification
- [ ] Human-review workflow for INCONCLUSIVE verdicts (analyst console)

---

## 7. Known limitations (disclose these)

1. AASIST engine undertrained on in-repo data (see §1); consensus masks this
   safely but reduces crisp-verdict rate.
2. Semantic fraud analysis (English regex rules + optional Gemini) covers
   English/Hinglish patterns only — regional-language expansion is open.
3. Single-node deployment; multi-worker scaling requires the Postgres store and
   a shared challenge backend (documented, not built).
4. The 3-Branch Ensemble (Wav2Vec2 path) requires the `ssl` extra and its own
   checkpoint; it is not part of the default consensus pair.
5. WhatsApp/VoIP capture claims in the pitch deck describe deployment
   architectures (SBC tap / on-device SDK) that are **not** implemented in this
   repository — this repo analyses PCM streams delivered to it.
