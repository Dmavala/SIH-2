import os
import subprocess
import imageio_ffmpeg
import soundfile as sf

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scam_call_data")
OUT_DIR = os.path.join(BASE_DIR, "processed")

os.makedirs(os.path.join(OUT_DIR, "scam"), exist_ok=True)
os.makedirs(os.path.join(OUT_DIR, "normal"), exist_ok=True)

def convert_to_wav16k(input_path, output_path):
    cmd = [
        FFMPEG_EXE,
        "-y",
        "-i", input_path,
        "-ar", "16000",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        output_path
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return res.returncode == 0

print("Converting SCAM CALLS...")
scam_in = os.path.join(BASE_DIR, "SCAM_CALLS")
scam_count = 0
for f in os.listdir(scam_in):
    in_file = os.path.join(scam_in, f)
    base_name = os.path.splitext(f)[0] + ".wav"
    out_file = os.path.join(OUT_DIR, "scam", base_name)
    if convert_to_wav16k(in_file, out_file):
        info = sf.info(out_file)
        print(f"  [SCAM] {f} -> {base_name} ({info.duration:.2f}s, {info.samplerate}Hz)")
        scam_count += 1
    else:
        print(f"  [FAIL] {f}")

print(f"\nConverted {scam_count} scam calls.")

print("\nConverting NORMAL CALLS...")
norm_in = os.path.join(BASE_DIR, "NORMAL_CALLS")
norm_count = 0
for f in os.listdir(norm_in):
    in_file = os.path.join(norm_in, f)
    base_name = os.path.splitext(f)[0] + ".wav"
    out_file = os.path.join(OUT_DIR, "normal", base_name)
    if convert_to_wav16k(in_file, out_file):
        info = sf.info(out_file)
        print(f"  [NORMAL] {f} -> {base_name} ({info.duration:.2f}s, {info.samplerate}Hz)")
        norm_count += 1
    else:
        print(f"  [FAIL] {f}")

print(f"\nConverted {norm_count} normal calls.")
