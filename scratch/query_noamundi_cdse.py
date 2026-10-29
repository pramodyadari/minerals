import urllib.request
import urllib.parse
import json
import sys

base = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
# Filter for Sentinel-2, MSIL2A, intersecting Noamundi (lon 85.50, lat 22.15) and containing T45QUE
filter_query = (
    "Collection/Name eq 'SENTINEL-2' and contains(Name, 'MSIL2A') and contains(Name, 'T45QUE') and "
    "OData.CSC.Intersects(area=geography'SRID=4326;POINT(85.50000 22.15000)')"
)
params = {
    "$filter": filter_query,
    "$top": "5",
    "$orderby": "ContentDate/Start desc",
    "$expand": "Attributes"
}
url = f"{base}?{urllib.parse.urlencode(params)}"
print(f"Querying URL: {url}")

req = urllib.request.Request(url, headers={"User-Agent": "AI-Mineral-Exploration-System/2.0"})
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        products = data.get("value", [])
        print(f"Found {len(products)} products:")
        for idx, p in enumerate(products):
            attrs = {a.get("Name"): a.get("Value") for a in p.get("Attributes", [])}
            print(f"[{idx+1}] Product:")
            print("  UUID:", p.get("Id"))
            print("  Name:", p.get("Name"))
            print("  ContentDate.Start:", p.get("ContentDate", {}).get("Start"))
            print("  ContentDate.End:", p.get("ContentDate", {}).get("End"))
            print("  CloudCover:", attrs.get("cloudCover"))
            print("  Online:", p.get("Online"))
            print("  ContentLength (bytes):", p.get("ContentLength"))
            print("  ContentLength (MB):", round(p.get("ContentLength", 0) / (1024*1024), 2) if p.get("ContentLength") else None)
            print("  S3Path:", p.get("S3Path"))
            print("  GeoFootprint:", json.dumps(p.get("GeoFootprint"))[:120] + "...")
except Exception as e:
    print(f"Error querying CDSE: {e}")
    sys.exit(1)
