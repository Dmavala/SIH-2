# Archived Evaluation Reports (STALE — do not quote)

These reports were generated against the **original procedurally-synthesized**
weights and demo audio (sine-harmonic constructions, circular train/test setup).
Their headline numbers (e.g. "98% ElevenLabs detection", "EER 4.17%") were
measured on synthetic distributions and are **not valid real-world claims**.

They are preserved for provenance only. To produce honest reports:

1. Retrain on real corpora: `python -m backend.training.train --data-dir ...`
2. Re-run the evaluation sweep against held-out real data
   (`python scripts/run_full_evaluation.py` — note it predates the consensus
   engine and needs updating before use).
3. Save the new JSON at the project root as `full_benchmark_report.json` —
   `GET /api/benchmark-report` will serve it automatically.
