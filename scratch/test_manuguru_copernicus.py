import urllib.request
import urllib.parse
import json

base = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
filter_query = "Collection/Name eq 'SENTINEL-2' and contains(Name, 'MSIL2A') and OData.CSC.Intersects(area=geography'SRID=4326;POINT(80.74 17.98)')"
params = {
    "$filter": filter_query,
    "$top": "3",
    "$orderby": "ContentDate/Start desc"
}
url = f"{base}?{urllib.parse.urlencode(params)}"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
        print(f"Manuguru scenes count: {len(data.get('value', []))}")
        for item in data.get("value", []):
            print("Name:", item.get("Name"))
            print("Date:", item.get("ContentDate", {}).get("Start"))
            pid = item.get("Id")
            att_url = f"{base}({pid})?$expand=Attributes"
            req2 = urllib.request.Request(att_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req2, timeout=5) as resp2:
                d2 = json.loads(resp2.read().decode())
                attrs = {a.get("Name"): a.get("Value") for a in d2.get("Attributes", [])}
                print("  Tile:", attrs.get("tileId"), "Cloud:", attrs.get("cloudCover"))
except Exception as e:
    print("Error:", e)
