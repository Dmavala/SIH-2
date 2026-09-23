"""
Lifecycle test: attack -> popup -> reset -> recovery -> re-attack.

Proves the exact bug the user reported is fixed:
  1. A synthetic attack escalates to CRITICAL and fires an out-of-band challenge.
  2. RESET_BUFFER (what modal-close now sends) yields RESET_ACK.
  3. Real audio afterwards produces live telemetry, frozen=False, no false alarm.
  4. A second attack RE-TRIGGERS the challenge (system never stays dead).

Run while a server is up:  python scripts/test_recovery_lifecycle.py [port]
"""

import asyncio
import glob
import json
import sys

import numpy as np
import soundfile as sf
import websockets

PORT = sys.argv[1] if len(sys.argv) > 1 else "8013"
URI = f"ws://127.0.0.1:{PORT}/ws/audio-stream"

REAL = "backend/demo_audio/samples/real_authentic_speech.wav"
FAKE = "backend/demo_audio/samples/real_deepfake_elevenlabs.wav"


async def send_file(ws, path, max_sec=8.0):
    data, sr = sf.read(path, dtype="float32")
    if data.ndim > 1:
        data = data.mean(axis=1)
    chunk = int(sr * 0.06)
    for i in range(0, min(len(data), int(sr * max_sec)), chunk):
        await ws.send((np.clip(data[i:i + chunk], -1, 1) * 32767).astype("<i2").tobytes())
        await asyncio.sleep(0.005)


async def drain(ws, quiet=1.2):
    out = []
    while True:
        try:
            out.append(json.loads(await asyncio.wait_for(ws.recv(), timeout=quiet)))
        except asyncio.TimeoutError:
            break
    return [(p.get("payload") or p) for p in out if p.get("type") == "TELEMETRY"]


async def main():
    samples = glob.glob("backend/demo_audio/samples/*.wav")
    assert any("authentic_speech" in p for p in samples), "real demo sample missing"
    assert any("deepfake_elevenlabs" in p for p in samples), "fake demo sample missing"

    async with websockets.connect(URI, max_size=None) as ws:
        await ws.recv()  # handshake

        # --- 1. Attack: challenge must fire ---
        await send_file(ws, FAKE)
        t1 = await drain(ws)
        ch1 = next((p.get("challenge") for p in t1 if p.get("challenge")), None)
        crit1 = any(p.get("status") == "CRITICAL_SYNTHETIC" for p in t1)
        print(f"1. ATTACK-1:   critical={crit1}  challenge_fired={bool(ch1)}")

        # --- 2. Reset (modal close) ---
        await ws.send(json.dumps({"command": "RESET_BUFFER"}))
        while True:
            m = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
            if m.get("type") == "RESET_ACK":
                break
        print("2. RESET_ACK   received")
        await drain(ws, 0.6)  # client drops stale pre-reset frames (FIFO)

        # --- 3. Real audio: telemetry must flow, no freeze, no false alarm ---
        await send_file(ws, REAL)
        t2 = await drain(ws)
        max_risk = max([p.get("instant_risk", 0) for p in t2] or [0])
        print(f"3. REAL AUDIO: frames={len(t2)}  frozen={any(p.get('is_frozen') for p in t2)}  "
              f"false_alarm={any(p.get('status') == 'CRITICAL_SYNTHETIC' for p in t2)}  max_risk={max_risk:.0f}")

        # --- 4. Attack again: system must re-trigger ---
        await send_file(ws, FAKE)
        t3 = await drain(ws)
        ch3 = next((p.get("challenge") for p in t3 if p.get("challenge")), None)
        crit3 = any(p.get("status") == "CRITICAL_SYNTHETIC" for p in t3)
        print(f"4. ATTACK-2:   critical={crit3}  challenge_re_fired={bool(ch3)}")

        ok = bool(ch1) and len(t2) > 0 and not any(p.get("is_frozen") for p in t2) \
            and not any(p.get("status") == "CRITICAL_SYNTHETIC" for p in t2) and bool(ch3)
        print("RESULT:", "PASS - full lifecycle recovered" if ok else "FAIL")
        sys.exit(0 if ok else 1)


asyncio.run(main())
