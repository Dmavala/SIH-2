import os
import soundfile as sf

scam_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scam_call_data", "SCAM_CALLS")
for name in os.listdir(scam_dir)[:10]:
    path = os.path.join(scam_dir, name)
    with open(path, "rb") as f:
        header = f.read(16)
    try:
        info = sf.info(path)
        print(f"{name}: VALID AUDIO ({info.format}, {info.subtype}, {info.samplerate}Hz, {info.duration:.2f}s)")
    except Exception as e:
        print(f"{name}: header={header.hex()} | error={e}")
