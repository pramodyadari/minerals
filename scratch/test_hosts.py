import sys
sys.path.append("backend/app")
from raster_ingestion_service import CopernicusDataAccessManager
import urllib.request

mgr = CopernicusDataAccessManager()
token = mgr.obtain_access_token(timeout_sec=30.0)
pid = "15cf3fdd-a44e-4f23-9c64-bbe5a300676e"

for host in ["zipper.dataspace.copernicus.eu", "catalogue.dataspace.copernicus.eu", "download.dataspace.copernicus.eu"]:
    url = f"https://{host}/odata/v1/Products({pid})/$value"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "User-Agent": "AI-Mineral-Exploration-System/2.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"{host} -> URL: {resp.geturl()}, Status: {resp.status}, Content-Type: {resp.headers.get('Content-Type')}, Content-Length: {resp.headers.get('Content-Length')}")
    except Exception as e:
        print(f"{host} -> Error: {e}")
