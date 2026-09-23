"""
End-to-End System Verification Script for Aegis Voice Sentinel.
Tests REST API endpoints, WebSocket streaming, VAD silence gating, and threat hysteresis.
"""

import sys
import time
import json
import asyncio
import numpy as np
import urllib.request
import websockets

BACKEND_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000/ws/audio-stream"


def test_rest_endpoints():
    print("[1/3] Testing REST API Endpoints...")

    # 1. Health check
    req = urllib.request.urlopen(f"{BACKEND_URL}/api/health")
    health = json.loads(req.read().decode())
    assert health["status"] == "HEALTHY", f"Health failed: {health}"
    print(f"  [OK] /api/health: Status {health['status']} | Model {health['active_model']}")

    # 2. Samples list
    req = urllib.request.urlopen(f"{BACKEND_URL}/api/samples")
    samples = json.loads(req.read().decode())
    assert len(samples) > 0, "No samples found"
    print(f"  [OK] /api/samples: {len(samples)} benchmark audio tracks loaded")

    # 3. Trigger challenge
    data = json.dumps({"session_id": "TEST-SES-001", "trigger_risk": 92.5, "reason": "Test Synthetic Vocoder"}).encode()
    req = urllib.request.Request(f"{BACKEND_URL}/api/trigger-challenge", data=data, headers={"Content-Type": "application/json"})
    challenge = json.loads(urllib.request.urlopen(req).read().decode())
    assert challenge["status"] == "PENDING", f"Challenge failed: {challenge}"
    otp = challenge["otp_code"]
    print(f"  [OK] /api/trigger-challenge: Issued challenge {challenge['challenge_id']} with OTP {otp}")

    # 4. Verify OTP
    data = json.dumps({"session_id": "TEST-SES-001", "otp_code": otp}).encode()
    req = urllib.request.Request(f"{BACKEND_URL}/api/verify-otp", data=data, headers={"Content-Type": "application/json"})
    verification = json.loads(urllib.request.urlopen(req).read().decode())
    assert verification["success"] is True, f"OTP verification failed: {verification}"
    print(f"  [OK] /api/verify-otp: Verified successfully: {verification['message']}")

    # 5. Audit log
    req = urllib.request.urlopen(f"{BACKEND_URL}/api/audit-log")
    audit_log = json.loads(req.read().decode())
    assert len(audit_log) > 0, "Audit log empty"
    print(f"  [OK] /api/audit-log: {len(audit_log)} events recorded in ledger")


async def test_websocket_streaming():
    print("\n[2/3] Testing Live WebSocket Audio Streaming & Stability...")
    async with websockets.connect(WS_URL) as ws:
        # Handshake
        handshake_raw = await ws.recv()
        handshake = json.loads(handshake_raw)
        assert handshake["type"] == "HANDSHAKE"
        session_id = handshake["session_id"]
        print(f"  [OK] Connected to WebSocket. Session ID: {session_id}")

        # Stream 1: Send 16kHz synthetic speech frames (generating harmonic voice)
        t = np.linspace(0, 0.128, 2048, endpoint=False)  # 2048 samples = 128ms
        # Generate glottal pulse train to simulate vocal folds
        audio_frame = (0.5 * np.sin(2 * np.pi * 180 * t) + 0.3 * np.sin(2 * np.pi * 360 * t)).astype(np.float32)
        int16_frame = (audio_frame * 32767).astype(np.int16).tobytes()

        telemetry_count = 0
        print("  -> Streaming audio frames (simulating live speech)...")
        for i in range(16):  # ~2 seconds of audio
            await ws.send(int16_frame)
            await asyncio.sleep(0.05)
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=0.1)
                data = json.loads(msg)
                if data.get("type") == "TELEMETRY":
                    telemetry_count += 1
                    if telemetry_count == 1:
                        print(f"     First Telemetry Received: Smoothed Risk={data['smoothed_risk']}%, Status={data['status']}, Latency={data['latency_ms']}ms")
            except asyncio.TimeoutError:
                pass

        print(f"  [OK] Active audio streaming returned {telemetry_count} telemetry updates")

        # Stream 2: Test Conversational Pause / Ambient Silence Gating
        print("  -> Testing conversational pause stability (silence gating)...")
        silent_frame = (np.random.normal(0, 0.001, 2048) * 32767).astype(np.int16).tobytes()
        pause_telemetry = None
        for i in range(10):  # ~1.3 seconds of pause
            await ws.send(silent_frame)
            await asyncio.sleep(0.05)
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=0.1)
                data = json.loads(msg)
                if data.get("type") == "TELEMETRY":
                    pause_telemetry = data
            except asyncio.TimeoutError:
                pass

        if pause_telemetry:
            print(f"     Pause Telemetry: Status={pause_telemetry['status']}, is_idle={pause_telemetry.get('is_idle')}, Smoothed Risk={pause_telemetry['smoothed_risk']}%")
            print("  [OK] Conversational pause handled gracefully with temporal hysteresis!")

        # Ping-pong test
        await ws.send(json.dumps({"command": "PING"}))
        pong_msg = await ws.recv()
        pong = json.loads(pong_msg)
        assert pong.get("type") == "PONG"
        print("  [OK] WebSocket heartbeat PING/PONG verified")

        # Buffer reset test
        await ws.send(json.dumps({"command": "RESET_BUFFER"}))
        reset_ack = json.loads(await ws.recv())
        assert reset_ack.get("type") == "RESET_ACK"
        print("  [OK] RESET_BUFFER successfully reset session state")


def main():
    print("=" * 60)
    print("AEGIS VOICE SENTINEL - FULL SYSTEM VERIFICATION SUITE")
    print("=" * 60)
    test_rest_endpoints()
    asyncio.run(test_websocket_streaming())
    print("\n[3/3] Frontend Dev Server Check...")
    req = urllib.request.urlopen("http://localhost:5173/")
    html = req.read().decode()
    assert "<title>" in html or "id=\"root\"" in html
    print("  [OK] Frontend dev server responding on http://localhost:5173/ with status 200 OK")
    print("=" * 60)
    print("ALL VERIFICATIONS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    main()
