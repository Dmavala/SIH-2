"""
Concurrent load test for the AEGIS backend.

Measures what a GoI deployment review will actually ask for: throughput and
latency percentiles under concurrency, for both lightweight (/api/health) and
inference-heavy (/api/analyze-file) endpoints.

Usage:
    python scripts/load_test.py --workers 8 --requests 40 --sample scam
"""

import argparse
import concurrent.futures as cf
import io
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DEFAULT_BASE = os.getenv("AEGIS_BASE_URL", "http://127.0.0.1:8000")


def find_sample(kind: str) -> str:
    import soundfile as sf  # noqa: F401  (ensures audio stack present)

    if kind == "real":
        cands = ["backend/demo_audio/samples", "large_benchmark_data/real"]
    else:
        cands = ["backend/demo_audio/samples", "large_benchmark_data/fake"]
    for d in cands:
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.lower().endswith((".wav", ".flac")):
                if kind == "fake" and not f.lower().startswith(("scam", "fake", "synth", "ai_", "el_")):
                    continue
                return os.path.join(d, f)
    raise SystemExit("No sample audio found for load test")


def multipart_body(filename: str, data: bytes, field: str = "file",
                   content_type: str = "audio/wav") -> tuple:
    boundary = "----aegisloadtest7d33c2"
    buf = io.BytesIO()
    buf.write(f"--{boundary}\r\n".encode())
    buf.write(
        f'Content-Disposition: form-data; name="{field}"; '
        f'filename="{filename}"\r\n'.encode()
    )
    buf.write(f"Content-Type: {content_type}\r\n\r\n".encode())
    buf.write(data)
    buf.write(f"\r\n--{boundary}--\r\n".encode())
    return buf.getvalue(), f"multipart/form-data; boundary={boundary}"


def timed_post(base: str, path: str, payload: bytes, content_type: str) -> tuple:
    req = urllib.request.Request(
        base + path, data=payload, method="POST",
        headers={"Content-Type": content_type},
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            resp.read()
            code = resp.status
        err = None
    except urllib.error.HTTPError as e:
        code = e.code
        err = str(e)[:120]
    except Exception as e:
        code = 0
        err = str(e)[:120]
    return (time.perf_counter() - t0) * 1000.0, code, err


def timed_get(base: str, path: str) -> tuple:
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(base + path, timeout=30) as resp:
            resp.read()
            code = resp.status
        err = None
    except urllib.error.HTTPError as e:
        code = e.code
        err = str(e)[:120]
    except Exception as e:
        code = 0
        err = str(e)[:120]
    return (time.perf_counter() - t0) * 1000.0, code, err


def run_endpoint(name: str, jobs, workers: int) -> dict:
    lat, codes, errors = [], {}, 0
    t_start = time.perf_counter()
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for ms, code, err in ex.map(lambda j: j(), jobs):
            lat.append(ms)
            codes[code] = codes.get(code, 0) + 1
            if err or code >= 500:
                errors += 1
    dur = time.perf_counter() - t_start
    lat.sort()
    n = len(lat)
    pct = lambda p: lat[min(n - 1, int(n * p / 100.0))]
    return {
        "endpoint": name,
        "requests": n,
        "concurrency": workers,
        "duration_s": round(dur, 2),
        "throughput_rps": round(n / dur, 2),
        "latency_ms": {"p50": round(pct(50), 1), "p95": round(pct(95), 1),
                       "p99": round(pct(99), 1), "max": round(lat[-1], 1),
                       "mean": round(statistics.mean(lat), 1)},
        "status_codes": codes,
        "errors": errors,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--requests", type=int, default=40,
                    help="Requests per endpoint")
    ap.add_argument("--sample", choices=["real", "fake"], default="fake")
    args = ap.parse_args()

    wav_path = find_sample(args.sample)
    with open(wav_path, "rb") as fh:
        wav_bytes = fh.read()
    print(f"[load] sample: {wav_path} ({len(wav_bytes)/1024:.0f} KB), "
          f"{args.workers} workers x {args.requests} requests per endpoint")
    print("[load] note: default analyze rate limit is low — for throughput "
          "numbers set AEGIS_RATE_ANALYZE_PER_MIN high on the server, e.g.\n"
          "       AEGIS_RATE_ANALYZE_PER_MIN=10000 python -m uvicorn backend.main:app")

    # --- health (control) ---
    health_jobs = [(lambda b=args.base: timed_get(b, "/api/health"))
                   for _ in range(args.requests)]
    results = [run_endpoint("GET /api/health", health_jobs, args.workers)]

    # --- inference ---
    infer_jobs = []
    body, ctype = multipart_body(os.path.basename(wav_path), wav_bytes)
    for _ in range(args.requests):
        infer_jobs.append((
            lambda b=args.base, d=body, ct=ctype: timed_post(
                b, "/api/analyze-file", d, ct)
        ))
    results.append(run_endpoint("POST /api/analyze-file", infer_jobs, args.workers))

    print(json.dumps(results, indent=2))
    out = os.path.join(ROOT, "load_test_report.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                   "results": results}, fh, indent=2)
    print(f"[load] written -> {out}")

    fails = [r for r in results if r["errors"]]
    if fails:
        print(f"[load] WARNING: {sum(f['errors'] for f in fails)} request errors")
        sys.exit(1)


if __name__ == "__main__":
    main()
