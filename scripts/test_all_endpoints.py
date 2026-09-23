import urllib.request
import json
import os

BASE_URL = 'http://127.0.0.1:8000'

def test_health():
    with urllib.request.urlopen(f'{BASE_URL}/api/health') as r:
        data = json.loads(r.read().decode())
        print('[PASS] /api/health:', data['status'], '| Active Model:', data['active_model'], '| Device:', data['device'])

def test_samples():
    with urllib.request.urlopen(f'{BASE_URL}/api/samples') as r:
        data = json.loads(r.read().decode())
        print(f'[PASS] /api/samples: {len(data)} benchmark and Indian scam scenarios loaded')

def test_audit():
    with urllib.request.urlopen(f'{BASE_URL}/api/audit-log') as r:
        data = json.loads(r.read().decode())
        print(f'[PASS] /api/audit-log: {len(data)} events recorded in ledger')

def test_set_model():
    req = urllib.request.Request(
        f'{BASE_URL}/api/set-model',
        data=json.dumps({'model': 'rawnet'}).encode(),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as r:
        res = json.loads(r.read().decode())
        assert res['active_model'] == 'RAWNET'
    
    req2 = urllib.request.Request(
        f'{BASE_URL}/api/set-model',
        data=json.dumps({'model': 'aasist'}).encode(),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req2) as r:
        res2 = json.loads(r.read().decode())
        assert res2['active_model'] == 'AASIST'
    print('[PASS] /api/set-model: Seamless dynamic model switching verified (AASIST <-> RawNet2)')

def test_generate_dossier():
    payload = {
        'session_id': 'SES-SIH-TEST',
        'threat_score': 98.2,
        'status': 'CRITICAL_SYNTHETIC',
        'forensics': {
            'pitch_mean': 180.0,
            'pitch_std': 25.0,
            'jitter_local': 0.002,
            'shimmer_local': 0.12,
            'phase_dispersion': 0.05,
            'ambient_noise_floor_db': -82.0
        },
        'anomalies': ['Neural Vocoder Phase Inconsistency', 'Pristine Digital Background Vacuum'],
        'case_metadata': {
            'case_no': 'NCRP/CYBER/2026/TEST-001',
            'fir_ref': 'FIR 104/2026 U/S 66D IT ACT',
            'police_station': 'Cyber Crime Police Station, Special Cell',
            'officer': 'Inspector Test'
        }
    }
    req = urllib.request.Request(
        f'{BASE_URL}/api/generate-dossier',
        data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as r:
        cert = json.loads(r.read().decode())
        print('[PASS] /api/generate-dossier: Section 63 BSA 2023 certificate generated:', cert['legal_header']['dossier_id'])

def test_analyze_file():
    sample_file = os.path.join('backend', 'demo_audio', 'samples', 'authentic_human_indian_accent.wav')
    with open(sample_file, 'rb') as f:
        file_bytes = f.read()

    boundary = '----BoundaryXYZ123'
    body = bytearray()
    body.extend(f'--{boundary}\r\n'.encode('utf-8'))
    body.extend(b'Content-Disposition: form-data; name="file"; filename="authentic_human_indian_accent.wav"\r\n')
    body.extend(b'Content-Type: audio/wav\r\n\r\n')
    body.extend(file_bytes)
    body.extend(b'\r\n')
    body.extend(f'--{boundary}\r\n'.encode('utf-8'))
    body.extend(b'Content-Disposition: form-data; name="telephony_mode"\r\n\r\n')
    body.extend(b'false\r\n')
    body.extend(f'--{boundary}--\r\n'.encode('utf-8'))

    req = urllib.request.Request(
        f'{BASE_URL}/api/analyze-file',
        data=bytes(body),
        headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
    )
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read().decode())
        print(f'[PASS] /api/analyze-file: Analyzed "{data["filename"]}" ({data["duration_sec"]}s) -> Risk: {data["analysis"]["risk_score"]}% ({data["analysis"]["status"]})')

if __name__ == '__main__':
    print('=' * 70)
    print('VERIFYING 100% OF BACKEND ENDPOINTS')
    print('=' * 70)
    test_health()
    test_samples()
    test_audit()
    test_set_model()
    test_generate_dossier()
    test_analyze_file()
    print('=' * 70)
    print('ALL BACKEND ENDPOINTS VERIFIED OPERATIONAL!')
    print('=' * 70)
