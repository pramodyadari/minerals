import urllib.request
import json

base = "https://dataspace.copernicus.eu"
pid = "3525011d-64dc-4c1c-9329-39b302f0fb0d"
url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products({pid})?$expand=Attributes"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
        print("Attributes for single product:")
        for a in data.get("Attributes", []):
            if "cloud" in a.get("Name", "").lower() or "tile" in a.get("Name", "").lower() or "instrument" in a.get("Name", "").lower() or "processor" in a.get("Name", "").lower():
                print(f"  {a.get('Name')}: {a.get('Value')}")
except Exception as e:
    print("Error:", e)
