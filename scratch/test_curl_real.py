import sys
import subprocess
import time
import os

sys.path.append("backend/app")
from raster_ingestion_service import CopernicusDataAccessManager

mgr = CopernicusDataAccessManager()
token = mgr.obtain_access_token(timeout_sec=30.0)
pid = "15cf3fdd-a44e-4f23-9c64-bbe5a300676e"
url = f"https://download.dataspace.copernicus.eu/odata/v1/Products({pid})/$value"
dest = "data/cache/temp_extract/test_curl.bin"

print(f"Requesting: {url}")
cmd = [
    "curl.exe",
    "-v",
    "-s",
    "-S",
    "-f",
    "-H", f"Authorization: Bearer {token}",
    "-o", dest,
    "--max-time", "15",
    url
]
t0 = time.time()
res = subprocess.run(cmd, capture_output=True, text=True)
t1 = time.time()
sz = os.path.getsize(dest) if os.path.exists(dest) else 0
print(f"Curl return code: {res.returncode}")
print(f"Curl stderr:\n{res.stderr[:800]}")
print(f"Downloaded: {sz / (1024**2):.2f} MB in {t1-t0:.2f}s ({sz / (1024**2) / (t1-t0):.2f} MB/s)")
if os.path.exists(dest):
    os.remove(dest)
