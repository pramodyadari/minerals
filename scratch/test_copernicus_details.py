import urllib.request
import urllib.parse
import json

base = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
filter_query = "Collection/Name eq 'SENTINEL-2' and contains(Name, 'MSIL2A') and OData.CSC.Intersects(area=geography'SRID=4326;POINT(80.74 17.98)')"
params = {
    "$filter": filter_query,
    "$top": "3",
    "$orderby": "ContentDate/Start desc",
    "$expand": "Attributes"
}
url = f"{base}?{urllib.parse.urlencode(params)}"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
        print(f"Products count: {len(data.get('value', []))}")
        for item in data.get("value", []):
            name = item.get("Name")
            date = item.get("ContentDate", {}).get("Start")
            attrs = {a.get("Name"): a.get("Value") for a in item.get("Attributes", [])}
            cloud = attrs.get("cloudCover")
            footprint = item.get("GeoFootprint")
            print("--- Product ---")
            print("Name:", name)
            print("Date:", date)
            print("Cloud:", cloud)
            print("Footprint keys/type:", type(footprint), list(footprint.keys()) if isinstance(footprint, dict) else str(footprint)[:60])
            print("Product ID:", item.get("Id"))
except Exception as e:
    print("Error:", e)
