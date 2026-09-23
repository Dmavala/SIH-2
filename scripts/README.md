# Maintenance & Evaluation Scripts

One-off operational scripts moved out of the repo root. Run from the project root:

```bash
python scripts/<name>.py
```

| Script | Purpose |
|---|---|
| `download_*.py` | Fetch benchmark datasets (ASVspoof-style, real-world scam samples) |
| `convert_scam_dataset.py` | Normalize downloaded scam audio to 16 kHz WAV |
| `check_scam_format.py` | Validate dataset formatting before training |
| `calibrate_with_realworld.py` | Threshold calibration against real-world samples |
| `run_full_evaluation.py` | Full benchmark sweep → JSON report |
| `run_large_scale_training_and_benchmark.py` | Long training + eval pipeline |
| `train_and_evaluate_scam_model.py` | Scam-scenario training/eval |
| `test_all_endpoints.py` | Integration test of all REST endpoints |
| `test_all_three_engines.py` | Cross-engine (AASIST/RawNet/Ensemble) checks |
| `test_full_system.py` | End-to-end system test |
| `build_simple_pdf.py`, `build_tech_stack_pdf.py`, `generate_pdf_report.py` | Report/PDF generators (contain hardcoded macOS paths — adapt before use) |

> NOTE: several of these reference machine-specific absolute paths
> (`/Users/...`, `C:/Users/...`). They are preserved as-is for provenance;
> update paths before reuse.
