import urllib.request
import sys
sys.path.append("backend/app")
from raster_ingestion_service import CopernicusDataAccessManager

mgr = CopernicusDataAccessManager()
token = mgr.obtain_access_token(timeout_sec=30.0)
pid = "15cf3fdd-a44e-4f23-9c64-bbe5a300676e"

hosts = [
    "catalogue.dataspace.copernicus.eu",
    "zipper.dataspace.copernicus.eu",
    "download.dataspace.copernicus.eu"
]

for host in hosts:
    url = f"https://{host}/odata/v1/Products({pid})/$value"
    print(f"\n--- Testing host: {host} ---")
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "User-Agent": "AI-Mineral-Exploration-System/2.0"
    })

    class CheckRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, r, fp, code, msg, headers, newurl):
            print(f"[{host}] Redirect {code} -> {newurl}")
            return super().redirect_request(r, fp, code, msg, headers, newurl)

    opener = urllib.request.build_opener(CheckRedirect)
    try:
        with opener.open(req, timeout=15) as resp:
            print(f"[{host}] Status: {resp.status}")
            print(f"[{host}] URL: {resp.geturl()}")
            print(f"[{host}] Content-Type: {resp.headers.get('Content-Type')}")
            print(f"[{host}] Content-Length: {resp.headers.get('Content-Length')}")
    except Exception as e:
        print(f"[{host}] Error: {e}")
