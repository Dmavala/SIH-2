import os
import urllib.request
import zipfile
import io

DEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scam_call_data")
os.makedirs(DEST_DIR, exist_ok=True)

URL = "https://raw.githubusercontent.com/CyberSorceress/Scam-Call-Detection/main/Data/dataset.zip"
print(f"Downloading dataset.zip from {URL} (~23 MB)...")

req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req) as resp:
    zip_bytes = resp.read()
    print(f"Downloaded {len(zip_bytes)} bytes. Extracting to {DEST_DIR}...")

with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
    z.extractall(DEST_DIR)
    print("Extraction complete! Extracted files:")
    for name in z.namelist()[:15]:
        print(" ", name)
    print(f"Total files in archive: {len(z.namelist())}")
